<template>
  <MonacoEditor :value="logs" language="plaintext" :theme="theme" :options="options" class="editor" />
</template>
<script>
import { h } from 'vue';
import MonacoEditor from 'vue-monaco';
import { getTaskLogs } from '../api';
MonacoEditor.render = () => h('div');

export default {
  name: "TaskLogs",
  props: ["taskId"],
  components: { MonacoEditor },
  data() {
    return {
      options: {
        automaticLayout: true,
        readOnly: true,
        domReadOnly: true,
      },
      lastLogLine: "",
      logs: "",
      maxLinesToFetch: 100,
      columns: [
        {key: "asctime", width: "calc(20%)", minWidth: "200px"},
        {key: "levelname", width: "calc(10%)", minWidth: "50px"},
        {key: "msg", width: "calc(70%)"},
      ],
      logUpdateTask: null,
      expandedItems: {},
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
      this.logs = "";
    },
    getLogs() {
      if (this.taskId) {
        getTaskLogs(
          this.taskId,
          this.lastLogLine,
          this.maxLinesToFetch
        ).then(resp => {
          if (resp.length > 0) {
            this.logs += "\n" + resp.map(x => `${x.data['asctime']} - ${x.data['levelname']} - ${x.data['msg']}`).join("\n");
            this.lastLogLine = resp[resp.length-1].id;
          }
          setTimeout(this.getLogs, 1000);
        });
      }
    },
    expand(id) {
      if (id in this.expandedItems) {
        this.expandedItems[id] = !this.expandedItems[id];
      } else {
        this.expandedItems[id] = true;
      }
    },
    expanded(id) {
      if (id in this.expandedItems) {
        return this.expandedItems[id];
      }
      return false;
    },
  }
}
</script>
<style>
.editor {
  width: 100%;
  height: 600px;
}
</style>
