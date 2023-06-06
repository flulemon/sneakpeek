<template>

  <q-page class="flex flex-top column q-py-md">
    <div class="text-h6 q-px-xl">
      New dynamic scraper
    </div>
    <q-separator />
  <MonacoEditor @change="updateCode" :value="code" language="python" :theme="theme" :options="options" class="editor" />
  </q-page>
</template>
<script>
import { h } from 'vue';
import MonacoEditor from 'vue-monaco';
MonacoEditor.render = () => h('div');

export default {
  name: "NewDynamicScraperPage",
  components: { MonacoEditor },
  data() {
    return {
      code: `
# Define the code for the scraper logic here
from sneakpeek.scraper_context import ScraperContext
from pydantic import BaseModel


# Scraper must define 'handler' function. Consider it to be the 'main' function of the scraper.
# All of the arguments (except the first 'ctx') will be passed using scraper config's 'args' or 'kwargs'
async def handler(ctx: ScraperContext, start_url: str) -> str:
    response = await ctx.get(start_url)
    content = await response.text()
    return {
        "success": True,
        "content": content
    }`,
      options: {
        automaticLayout: true
      }
    }
  },
  computed: {
    theme() {
      return this.$q.dark.isActive ? "vs-dark": "vs";
    }
  },
  methods: {
    updateCode(value) {
      this.code = value;
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
