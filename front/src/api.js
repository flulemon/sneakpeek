import { SessionStorage } from 'quasar';

function rpc(method, params) {
  return fetch(
    process.env.JSONRPC_ENDPOINT || "/api/v1/jsonrpc",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 0,
        method: method,
        params: params,
      })
    }
  ).then(response => {
    if (response.ok) {
      return response.json();
    } else {
      throw Error(response.statusText);
    }
  }).then(data => {
    if (data.error) {
      throw Error(data.error.message);
    }
    return data.result;
  });
}

export function getScrapers() {
  return rpc("get_scrapers", {});
}

export function getScraper(id) {
  return rpc("get_scraper", {id: id});
}

export function getScraperJobs(id) {
  return rpc("get_task_instances", {task_name: id});
}

export function getTask(id) {
  return rpc("get_task_instance", {task_id: id});
}

export function getTaskLogs(id, last_log_line_id, max_lines) {
  return rpc(
    "get_task_logs",
    {
      task_id: id,
      last_log_line_id: last_log_line_id,
      max_lines: max_lines
    }
  );
}

export function getScraperHandlers() {
  return rpc("get_scraper_handlers", {});
}

export function getSchedules() {
  return rpc("get_schedules", {});
}

export function getPriorities() {
  return rpc("get_priorities", {});
}

export function enqueueScraper(id) {
  return rpc("enqueue_scraper", {scraper_id: id, priority: 0});
}
export function createScraper(scraper) {
  return rpc("create_scraper", {scraper: scraper});
}


export function updateScraper(scraper) {
  return rpc("update_scraper", {scraper: scraper});
}

export function deleteScraper(id) {
  return rpc("delete_scraper", {id: id});
}

export function isReadOnly() {
  const value = SessionStorage.getItem("is_storage_read_only");
  if (value != null) return Promise.resolve(value);
  return rpc("is_read_only", {})
    .then(result => {
      SessionStorage.set("is_storage_read_only", result);
      return result;
    });
}

export function runEphemeralScraperTask(config, handler, state, priority) {
  return rpc(
    "run_ephemeral",
    {
      task: {
        scraper_config: config,
        scraper_handler: handler,
        scraper_state: state,
      },
      priority: priority,
    }
  );
}
