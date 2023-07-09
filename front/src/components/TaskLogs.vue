<template>
  <q-virtual-scroll
      type="table"
      style="max-height: 70vh"
      :virtual-scroll-item-size="48"
      :virtual-scroll-sticky-size-start="48"
      :virtual-scroll-sticky-size-end="32"
      :items="logs"
      v-slot="{ item: row, index }"
    >
    <tr :key="index">
        <td v-for="col in columns" :key="index + '-' + col">
          {{ row.data[col] }}
        </td>
      </tr>
  </q-virtual-scroll>
</template>
<script>
import { getTaskLogs } from '../api';

export default {
  name: "TaskLogs",
  props: ["taskId"],
  data() {
    return {
      lastLogLine: "",
      logs: [],
      maxLinesToFetch: 100,
      columns: [
        "asctime",
        "levelname",
        "msg"
      ],
      logUpdateTask: null,
    };
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
          this.logs = resp;
          setTimeout(this.getLogs, 1000);
        });
      }
    }
  }
}
</script>
