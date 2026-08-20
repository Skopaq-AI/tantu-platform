output "trigger_ids" { value={for k,v in google_cloudbuild_trigger.services: k=>v.id} }
