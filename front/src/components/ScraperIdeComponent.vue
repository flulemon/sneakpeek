<template>
  <div class="flex flex-top column" style="width: 100%;">
    <MonacoEditor :value="code" @change="updateCode" class="editor"
                  language="python" :theme="theme" :options="options" />
    <div class="q-mt-md">
      <div class="flex column q-px-xl" v-if="args && Object.keys(args).length > 0">
        <div class="text-h6">
          Session arguments
        </div>
        <div v-for="arg in Object.keys(args)" :key="arg" class="flex row items-baseline">
          <q-input v-model="args[arg]" :label="arg" dense class="q-mr-sm arg-input" />
        </div>
        <div class="q-mt-md flex row justify-start">
          <q-btn @click="run" size="sm" class="q-mr-sm" >
            <q-icon name="fa-solid fa-bug" class="q-mr-sm" :loading="runLoading" />
            Debug
          </q-btn>
          <q-btn size="sm" class="q-mr-sm" v-if="enableSaveBtn" @click="() => $emit('save', this.scraperConfig)">
            <q-icon name="fa-solid fa-save" class="q-mr-sm" />
            Save scraper
          </q-btn>
        </div>
      </div>
    </div>
    <div class="q-mt-lg" v-if="lastTaskId">
      <div class="text-h6 q-px-xl">
        Logs
      </div>
      <task-logs :task-id="lastTaskId" />
    </div>
  </div>
</template>
<script>
import { h } from 'vue';
import MonacoEditor from 'vue-monaco';
import { runEphemeralScraperTask } from '../api';
import TaskLogs from '../components/TaskLogs.vue';
MonacoEditor.render = () => h('div');

export default {
  name: "ScraperIdeComponent",
  components: { MonacoEditor, TaskLogs },
  props: ["modelValue", "enableSaveBtn"],
  emits: ['update:modelValue', "save"],
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
        "content": content[:50]
    }`,
      options: {
        // automaticLayout: true,
      },
      lastTaskId: null,
      args: {},
      runLoading: false,
    }
  },
  created() {
    if (this.modelValue && this.modelValue.params) {
      this.code = this.modelValue.params.source_code;
      this.args = this.modelValue.params.kwargs;
    } else {
      this.parseArgs();
    }
  },
  computed: {
    theme() {
      return this.$q.dark.isActive ? "vs-dark": "vs";
    },
    scraperConfig() {
      return {
        params: {
          source_code: this.code,
          kwargs: this.args,
        },
      }
    }
  },
  watch: {
    args: {
      deep: true,
      handler(val) {
        this.$emit('update:modelValue', this.scraperConfig);
      }
    }
  },
  methods: {
    updateCode(event) {
      if (typeof event === 'string' || event instanceof String) {
        this.code = event;
        this.parseArgs();
        this.$emit('update:modelValue', this.scraperConfig);
      }
    },
    run() {
      this.runLoading = true;
      runEphemeralScraperTask(
        {
          params: {
            source_code: this.code,
            args: Object.values(this.args),
          },
        },
        "dynamic_scraper",
        1,
      )
      .then((resp) => {
        this.lastTaskId = resp.id;
        this.$q.notify({
          message: `Started debug session`,
          color: "positive",
        });
      })
      .catch(error => this.$q.notify({
        message: `Failed to start debug session: ${error}`,
        color: "negative",
      }))
      .finally(() => this.runLoading = false);
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
    },
    save() {
      this.saveLoading = true;
      runEphemeralScraperTask(
        {
          params: {
            source_code: this.code,
            args: Object.values(this.args),
          },
        },
        "dynamic_scraper",
        1,
      )
      .then((resp) => {
        this.lastTaskId = resp.id;
        this.$q.notify({
          message: `Successfully created scraper`,
          color: "positive",
        });
      })
      .catch(error => this.$q.notify({
        message: `Failed to save scraper: ${error}`,
        color: "negative",
      }))
      .finally(() => this.saveLoading = false);
    }
  }
};
</script>
<style>
.editor {
  width: 100%;
  min-height: 600px;
  /* height: 600px; */
  height: 100%;
}
.arg-input {
  width: 100%;
}
</style>
