#![cfg_attr(not(debug_assertions), deny(warnings))]

use std::process::Command;

fn run_cmd(args: &[&str]) -> (i32, String, String) {
    let output = Command::new("systemctl")
        .args(args)
        .output();

    match output {
        Ok(o) => (
            o.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&o.stdout).to_string(),
            String::from_utf8_lossy(&o.stderr).to_string(),
        ),
        Err(e) => (-1, String::new(), e.to_string()),
    }
}

#[tauri::command]
fn get_service_status(service: &str) -> Result<serde_json::Value, String> {
    let (_rc, _out, _) = run_cmd(&["--user", "is-active", service]);

    let (rc2, out2, _) = run_cmd(&["--user", "show", "-p", "SubState", "--value", service]);
    if rc2 == 0 {
        let sub = out2.trim();
        if sub == "running" || sub == "exited" {
            return Ok(serde_json::json!({
                "ok": true,
                "status": "active",
                "substate": sub
            }));
        }
    }

    Ok(serde_json::json!({ "ok": true, "status": "inactive" }))
}

#[tauri::command]
fn execute_service_action(service: &str, action: &str) -> Result<serde_json::Value, String> {
    match action {
        "start" => {
            let (rc, _, err) = run_cmd(&["--user", "start", service]);
            if rc == 0 {
                Ok(serde_json::json!({ "ok": true, "message": "Started" }))
            } else {
                Ok(serde_json::json!({ "ok": false, "error": err.trim().to_string() }))
            }
        }
        "stop" => {
            let (rc, _, err) = run_cmd(&["--user", "stop", service]);
            if rc == 0 {
                Ok(serde_json::json!({ "ok": true, "message": "Stopped" }))
            } else {
                Ok(serde_json::json!({ "ok": false, "error": err.trim().to_string() }))
            }
        }
        "restart" => {
            let _ = run_cmd(&["--user", "daemon-reload"]);
            let (rc, _, err) = run_cmd(&["--user", "restart", service]);
            if rc == 0 {
                Ok(serde_json::json!({ "ok": true, "message": "Restarted" }))
            } else {
                Ok(serde_json::json!({ "ok": false, "error": err.trim().to_string() }))
            }
        }
        _ => Ok(serde_json::json!({ "ok": false, "error": "Unknown action".to_string() })),
    }
}

#[tauri::command]
fn open_service_log(service: &str) -> Result<(), String> {
    let terminals = ["gnome-terminal", "kitty", "alacritty", "xterm"];
    for term in &terminals {
        let output = std::process::Command::new("which").arg(term).output();

        if let Ok(output) = output {
            if output.status.success() {
                let cmd = format!(
                    "journalctl --user -u {} -f --no-pager; exec bash",
                    service
                );
                let _ = std::process::Command::new(term)
                    .args(&["bash", "-c", &cmd])
                    .spawn();
                return Ok(());
            }
        }
    }

    let (rc, out, _) = run_cmd(&[
        "--user",
        "journalctl",
        "-u",
        service,
        "-n",
        "50",
        "--no-pager",
    ]);
    if rc == 0 {
        println!("{}", out);
    } else {
        println!("Failed to get logs for {}", service);
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_service_status,
            execute_service_action,
            open_service_log,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
