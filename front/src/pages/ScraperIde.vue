<template>
  <q-page class="flex flex-top column q-py-md">
    <div class="text-h6 q-px-xl flex row">
      Scraper IDE
    </div>
    <q-separator />
  <MonacoEditor :value="code" @change="updateCode" language="python" :theme="theme" :options="options" class="editor" />
  <q-separator class="q-mt-lg q-mb-sm" />
  <div>
    <div class="text-h6 q-px-xl flex row">
      Debugger
    </div>
    <div class="flex column q-px-xl" v-if="args && Object.keys(args).length > 0">
      <div class="text">
        Session arguments
      </div>
      <div v-for="arg in Object.keys(args)" :key="arg" class="flex row items-baseline">
        <q-input v-model="args[arg]" :label="arg" dense size="sm" class="q-mr-sm arg-input" />
      </div>
      <div class="q-mt-md flex row justify-start">
        <q-btn @click="run" size="sm" class="q-mr-sm" >
          <q-icon name="fa-solid fa-play" class="q-mr-sm" />
          Run
        </q-btn>
        <q-btn @click="run" size="sm">
          <q-icon name="fa-solid fa-save" class="q-mr-sm" />
          Save
        </q-btn>
      </div>
    </div>
  </div>
  <div class="q-mt-lg" v-if="lastTaskId">
    <div class="text q-px-xl q-mb-md">
      Logs
    </div>
    <task-logs :task-id="lastTaskId" />
  </div>
  </q-page>
</template>
<script>
import { h } from 'vue';
import MonacoEditor from 'vue-monaco';
import { runEphemeralScraperTask } from '../api';
import TaskLogs from '../components/TaskLogs.vue';
MonacoEditor.render = () => h('div');

export default {
  name: "ScraperIde",
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
      args: {}
    }
  },
  created() {
    this.parseArgs();
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
        this.parseArgs();
      }
    },
    run() {
      runEphemeralScraperTask(
        {
          params: {
            source_code: this.code,
            args: Object.values(this.args),
          },
        },
        "dynamic_scraper",
        1,
      ).then((resp) => {
        this.lastTaskId = resp.id;
      });
    },
    parseArgs() {
      const args = /async def handler\(ctx[^,]+,(?<args>[^\)]+)\)/gm.exec(this.code);
        if (args && args.length > 0) {
          const parsedArgs = args.groups.args.split(",").map(a => a.split(":")[0].trim()).filter(a => a.length > 0);
          Object.keys(this.args).forEach(a => {
            if (!parsedArgs.includes(a)) {
              delete this.args[a];
            }
          });
          parsedArgs.forEach(a => {
            if (!(a in this.args)) {
              this.args[a] = "";
            }
          });
        }
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
.arg-input {
  width: 100%;
}
</style>
