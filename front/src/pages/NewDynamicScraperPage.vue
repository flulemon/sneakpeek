<template>

  <q-page class="flex flex-top column q-py-md">
    <div class="text-h6 q-px-xl flex row">
      New dynamic scraper
      <q-space />
      <q-btn @click="run" size="sm">
        <q-icon name="fa-solid fa-play" class="q-mr-sm" />
        Run
      </q-btn>
    </div>
    <q-separator />
  <MonacoEditor :value="code" @change="updateCode" language="python" :theme="theme" :options="options" class="editor" />
  <task-logs :task-id="lastTaskId" />
  </q-page>
</template>
<script>
import { h } from 'vue';
import MonacoEditor from 'vue-monaco';
import { runEphemeralScraperTask } from '../api';
import TaskLogs from '../components/TaskLogs.vue';
MonacoEditor.render = () => h('div');

export default {
  name: "NewDynamicScraperPage",
  components: { MonacoEditor, TaskLogs },
  data() {
    return {
      code: `
# Define the code for the scraper logic here
import logging

from pydantic import BaseModel
from sneakpeek.scraper.model import ScraperContextABC


# Scraper must define 'handler' function. Consider it to be the 'main' function of the scraper.
# All of the arguments (except the first 'ctx') will be passed using scraper config's 'args' or 'kwargs'
async def handler(ctx: ScraperContextABC, start_url: str) -> str:
    logging.info(f"Downloading {start_url}")
    response = await ctx.get(start_url)
    content = await response.text()
    logging.info(f"Received {content[:50]}")
    return {
        "success": True,
        "content": content
    }`,
      options: {
        automaticLayout: true
      },
      lastTaskId: null,
    }
  },
  computed: {
    theme() {
      return this.$q.dark.isActive ? "vs-dark": "vs";
    }
  },
  methods: {
    updateCode(event) {
      if (typeof event === 'string' || event instanceof String) {
        this.code = event;
      }
    },
    run() {
      runEphemeralScraperTask(
        {
          params: {
            source_code: this.code,
            args: ["https://vk.com"],
          },
        },
        "dynamic_scraper",
        1,
      ).then((resp) => {
        console.log(resp);
        this.lastTaskId = resp.id;
      });
    }
  }
};
</script>
<style>
.editor {
  width: 100%;
  height: 600px;
  padding-top: 15px;
}
</style>
