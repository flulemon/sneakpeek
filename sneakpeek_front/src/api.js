import { SessionStorage } from 'quasar';

function rpc(method, params) {
  return fetch(
    "http://localhost:8080/api/v1/jsonrpc",
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
  return rpc("get_scraper_jobs", {scraper_id: id});
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

export function createOrUpdateScraper(scraper) {
  let method = "update_scraper";
  if (scraper.id == null) {
    scraper.id = -1;
    method = "create_scraper";
  }
  return rpc(method, {scraper: scraper});
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
