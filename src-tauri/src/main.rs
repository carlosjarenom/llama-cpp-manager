#![cfg_attr(not(debug_assertions), deny(warnings))]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Command;

// ── Environment-aware command runner ────────────────────────────

/// Run a shell command, ensuring D-Bus env vars are passed so
/// `systemctl --user` works even when launched from a Tauri GUI
/// (which may not inherit the user session's D-Bus address).
fn run_cmd(cmd: &str, args: &[&str]) -> (i32, String, String) {
    let mut c = Command::new(cmd);
    c.args(args);

    // Pass through D-Bus session environment (required for systemctl --user)
    if let Ok(dir) = std::env::var("XDG_RUNTIME_DIR") {
        c.env("XDG_RUNTIME_DIR", &dir);
    }
    if let Ok(addr) = std::env::var("DBUS_SESSION_BUS_ADDRESS") {
        c.env("DBUS_SESSION_BUS_ADDRESS", &addr);
    }

    match c.output() {
        Ok(o) => (
            o.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
        ),
        Err(e) => (-1, String::new(), e.to_string()),
    }
}

// ── Data models ─────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug)]
struct ModelConfig {
    key: String,
    name: String,
    service: String,
    port: u16,
    model_path: String,
    color: String,
}

fn get_models() -> Vec<ModelConfig> {
    vec![
        ModelConfig {
            key: "27b".into(),
            name: "Qwen3.6-27B".into(),
            service: "llama-cpp-server".into(),
            port: 8002,
            model_path: "/home/carlos/.cache/llama.cpp/models/Qwen_Qwen3.6-27B-Q4_K_M.gguf"
                .into(),
            color: "#0099e6".into(),
        },
        ModelConfig {
            key: "35b".into(),
            name: "Qwen3.6-35B MoE".into(),
            service: "llama-cpp-server-35b".into(),
            port: 8003,
            model_path: "/home/carlos/.cache/llama.cpp/models/Qwen_Qwen3.6-35B-A3B-UD-IQ4_NL.gguf"
                .into(),
            color: "#e67300".into(),
        },
    ]
}

// ── Tauri commands ──────────────────────────────────────────────

/// Returns list of configured models
#[tauri::command]
fn list_models() -> Vec<ModelConfig> {
    get_models()
}

/// Check if a systemd user service is active
#[tauri::command]
fn check_service(service: String) -> Result<HashMap<String, String>, String> {
    let mut result = HashMap::new();

    // Check substate
    let (rc, out, _err) = run_cmd("systemctl", &["--user", "show", "-p", "SubState", "--value", &service]);
    if rc == 0 {
        result.insert("substate".into(), out.trim().to_string());
    } else {
        result.insert("substate".into(), "unknown".into());
        // Also check if the service unit exists
        let (rc2, _, err2) = run_cmd("systemctl", &["--user", "cat", &service]);
        if rc2 != 0 {
            result.insert("error".into(), err2.trim().to_string());
        }
    }

    // Derive simple active/inactive
    let sub = result.get("substate").map(|s| s.as_str()).unwrap_or("unknown");
    if sub == "running" || sub == "exited" {
        result.insert("status".into(), "active".into());
    } else {
        result.insert("status".into(), "inactive".into());
    }

    Ok(result)
}

/// Start / stop / restart a systemd user service
#[tauri::command]
fn control_service(service: String, action: String) -> Result<HashMap<String, String>, String> {
    let mut result = HashMap::new();

    let (rc, out, err) = match action.as_str() {
        "start" => run_cmd("systemctl", &["--user", "start", &service]),
        "stop" => run_cmd("systemctl", &["--user", "stop", &service]),
        "restart" => {
            let _ = run_cmd("systemctl", &["--user", "daemon-reload"]);
            run_cmd("systemctl", &["--user", "restart", &service])
        }
        _ => return Err(format!("Unknown action: {}", action)),
    };

    if rc == 0 {
        result.insert("ok".into(), "true".into());
        result.insert("message".into(), format!("Service {} successfully", action));
    } else {
        result.insert("ok".into(), "false".into());
        result.insert(
            "error".into(),
            if !err.is_empty() { err.trim().to_string() } else { out.trim().to_string() },
        );
    }

    Ok(result)
}

/// Health check: try to reach the OpenAI-compatible /v1/models endpoint
#[tauri::command]
fn health_check(port: u16) -> Result<HashMap<String, String>, String> {
    let mut result = HashMap::new();
    let url = format!("http://127.0.0.1:{}/v1/models", port);

    let (rc, out, _err) = run_cmd(
        "curl",
        &["-s", "--max-time", "5", "-o", "/dev/null", "-w", "%{http_code}", &url],
    );

    if rc == 0 && out.trim() == "200" {
        result.insert("status".into(), "ok".into());
        result.insert("port".into(), port.to_string());
    } else {
        result.insert("status".into(), "error".into());
        result.insert("port".into(), port.to_string());
        let detail = if rc != 0 {
            format!("curl exit {}", rc)
        } else {
            format!("HTTP {}", out.trim())
        };
        result.insert("detail".into(), detail);
    }

    Ok(result)
}

/// Get recent journal log lines for a service (returns last N lines)
#[tauri::command]
fn get_logs(service: String, lines: Option<u32>) -> Result<String, String> {
    let n = lines.unwrap_or(50);
    let (rc, out, err) = run_cmd(
        "journalctl",
        &[
            "--user", "-u", &service, "-n", &n.to_string(), "--no-pager", "--no-utc",
        ],
    );

    if rc == 0 {
        Ok(out)
    } else {
        Err(if !err.is_empty() { err } else { format!("journalctl failed (exit {})", rc) })
    }
}

/// Download a model file from Hugging Face using huggingface-cli
/// Progress is streamed via Tauri events.
#[tauri::command]
async fn download_model(
    _app_handle: tauri::AppHandle,
    repo_id: String,
    filename: String,
    dest: String,
) -> Result<HashMap<String, String>, String> {
    let mut result = HashMap::new();

    // Ensure destination directory exists
    if let Some(parent) = std::path::Path::new(&dest).parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            return Err(format!("Cannot create directory: {}", e));
        }
    }

    let full_dest = format!("{}{}", dest, std::path::MAIN_SEPARATOR);

    let output = Command::new("huggingface-cli")
        .args(&["download", &repo_id, &filename, "--local-dir", &full_dest])
        .output();

    match output {
        Ok(o) if o.status.success() => {
            // Check if file actually exists after download
            let file_exists = std::path::Path::new(&dest).join(&filename).exists();
            if file_exists {
                let full = format!("{}/{}", dest, filename);
                let metadata = std::fs::metadata(&full)
                    .map(|m| m.len())
                    .unwrap_or(0);
                let size_gb = (metadata as f64) / (1024.0 * 1024.0 * 1024.0);
                result.insert("ok".into(), "true".into());
                result.insert(
                    "message".into(),
                    format!("Downloaded {} ({:.1} GB)", filename, size_gb),
                );
            } else {
                result.insert("ok".into(), "false".into());
                result.insert("error".into(), "File not found after download".into());
            }
            Ok(result)
        }
        Ok(o) => {
            let stderr = String::from_utf8_lossy(&o.stderr);
            let code = o.status.code().unwrap_or(-1);
            Err(format!("huggingface-cli failed (exit {}): {}", code, stderr.lines().last().unwrap_or("")))
        }
        Err(e) => Err(format!("Cannot run huggingface-cli: {}", e)),
    }
}

/// Verify a model file exists and return its size
#[tauri::command]
fn verify_model(path: String) -> Result<HashMap<String, String>, String> {
    let mut result = HashMap::new();
    let p = std::path::Path::new(&path);

    if p.exists() {
        let metadata = std::fs::metadata(p)
            .map(|m| m.len())
            .unwrap_or(0);
        let size_mb = (metadata as f64) / (1024.0 * 1024.0 * 1024.0);
        result.insert("exists".into(), "true".into());
        result.insert("size_gb".into(), format!("{:.1}", size_mb));
        result.insert("path".into(), path);
        Ok(result)
    } else {
        result.insert("exists".into(), "false".into());
        result.insert("path".into(), path);
        Ok(result)
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            list_models,
            check_service,
            control_service,
            health_check,
            get_logs,
            download_model,
            verify_model,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
