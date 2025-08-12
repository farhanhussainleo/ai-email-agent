import os, json, csv, io, logging, string
import azure.functions as func
from azure.communication.email import EmailClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def jresp(body: dict, status: int) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=status)

@app.route(route="send_email", methods=["POST"])
def send_email(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # --- Content-Type + JSON parsing
        if not (req.headers.get("Content-Type", "")).lower().startswith("application/json"):
            return jresp({"error": "Content-Type must be application/json"}, 415)
        try:
            data = req.get_json()
        except ValueError:
            return jresp({"error": "Invalid JSON body"}, 400)

        # DEBUG: log exactly what Copilot sent
        logging.info("DEBUG payload from Copilot Studio: %s", json.dumps(data, ensure_ascii=False))

        # --- Required fields
        subject_raw = (data.get("subject") or "").strip()
        body_raw    = (data.get("body") or "").strip()
        if not subject_raw or not body_raw:
            missing = [k for k,v in {"subject": subject_raw, "body": body_raw}.items() if not v]
            return jresp({"ok": False, "error": "Missing required fields", "missing": missing,
                          "receivedPayload": data}, 400)

        subject_tmpl = string.Template(subject_raw)
        body_tmpl    = string.Template(body_raw)

        globals_vars = data.get("vars") or {}
        if not isinstance(globals_vars, dict):
            return jresp({"ok": False, "error": "'vars' must be an object/dict", "receivedPayload": data}, 400)

        # --- Build recipients
        rows = []
        recips = data.get("recipients")
        if isinstance(recips, str):
            recips = [r.strip() for r in recips.split(",") if r.strip()]
        if isinstance(recips, list):
            rows = [{"email": r.strip()} for r in recips if isinstance(r, str) and r.strip()]

        if not rows and "csvText" in data:
            csv_file = io.StringIO(data["csvText"])
            reader   = csv.DictReader(csv_file)
            if not reader.fieldnames or "email" not in [h.strip() for h in reader.fieldnames]:
                return jresp({"ok": False, "error": "CSV must include a header named 'email'.",
                              "receivedPayload": data}, 400)
            rows = [row for row in reader if (row.get("email") or "").strip()]

        if not rows:
            return jresp({"ok": False, "error": "Provide recipients via 'recipients' (string or array) or 'csvText'.",
                          "receivedPayload": data}, 400)

        # --- Env/config
        acs_conn = os.getenv("ACS_CONNECTION_STRING")
        sender   = os.getenv("ACS_SENDER_EMAIL")
        if not acs_conn or not sender:
            return jresp({"ok": False, "error": "Server misconfiguration: missing ACS_CONNECTION_STRING or ACS_SENDER_EMAIL",
                          "receivedPayload": data}, 500)

        client  = EmailClient.from_connection_string(acs_conn)
        results = []

        # --- Send loop
        for row in rows:
            email = (row.get("email") or "").strip()
            if not email:
                continue

            subs = {**globals_vars, **row}
            personal_subj = subject_tmpl.safe_substitute(subs)
            personal_body = body_tmpl.safe_substitute(subs)

            message = {
                "senderAddress": sender,
                "content": {"subject": personal_subj, "plainText": personal_body},
                "recipients": {"to": [{"address": email}]}
            }

            try:
                poller = client.begin_send(message)
                result = poller.result()  # SendEmailResult
                message_id = getattr(result, "message_id", None)
                if message_id is None and isinstance(result, dict):
                    message_id = result.get("message_id") or result.get("id")
                results.append({"email": email, "messageId": message_id})
            except Exception as send_exc:
                logging.exception("Send failed for %s", email)
                results.append({"email": email, "error": str(send_exc)})

        ok_count = len([r for r in results if r.get("messageId")])
        resp = {
            "ok": ok_count > 0,
            "okCount": ok_count,
            "errorCount": len(results) - ok_count,
            "receivedPayload": data,
            "results": results
        }
        return jresp(resp, 200)

    except Exception as exc:
        logging.exception("Unhandled server error")
        return jresp({"ok": False, "error": "Unhandled server error", "details": str(exc)}, 500)
