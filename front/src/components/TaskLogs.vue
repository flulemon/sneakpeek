<template>
  <q-infinite-scroll class="q-pa-sm bg-blue-grey-10">
    <pre v-for="(item, index) in logs" :key="index" :class="`log-line q-pa-none q-ma-none text-${getLogLevelTextColor(item.data.levelname)}`"
    >{{ item.data.asctime }}][{{ item.data.levelname.padEnd(8) }}] {{ item.data.msg }}</pre>
  </q-infinite-scroll>
</template>
<script>
import { getTaskLogs } from '../api';

export default {
  name: "TaskLogs",
  props: ["taskId"],
  data() {
    return {
      options: {
        readOnly: true,
        domReadOnly: true,
      },
      lastLogLine: "",
      logs: [],
      maxLinesToFetch: 100,
      logUpdateTask: null,
    };
  },
  computed: {
    theme() {
      return this.$q.dark.isActive ? "vs-dark": "vs";
    }
  },
  watch: {
    taskId() {
      this.init();
    }
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      if (this.taskId) {
        this.clean();
        this.getLogs();
      }
    },
    clean() {
      if (this.logUpdateTask) {
        clearTimeout(this.logUpdateTask);
        this.logUpdateTask = null;
      }
      this.lastLogLine = "";
      this.logs = [];
    },
    getLogs() {
      if (this.taskId) {
        getTaskLogs(
          this.taskId,
          this.lastLogLine,
          this.maxLinesToFetch
        ).then(resp => {
          if (resp.length > 0) {
            this.logs = this.logs.concat(resp);
            this.lastLogLine = resp[resp.length-1].id;
          }
          setTimeout(this.getLogs, 1000);
        });
      }
    },
    getLogLevelTextColor(level) {
      switch(level) {
        case "CRITICAL": return "deep-purple-5";
        case "ERROR": return "red-14";
        case "WARNING": return "amber-10";
        default:
          return "grey-5";
      }
    },
  }
}
</script>
<style>
.logs {
  width: 100%;
  max-height: 600px;
  overflow: auto;
}
.log-line {
  font-family: Consolas,Monaco,Andale Mono,Ubuntu Mono,monospace;
  font-size: 14px;
}
</style>
