<template>
  <q-virtual-scroll
      type="table"
      style="max-height: 70vh; max-width: 100%;"
      :virtual-scroll-item-size="48"
      :virtual-scroll-sticky-size-start="48"
      :virtual-scroll-sticky-size-end="32"
      :items="logs"
      v-slot="{ item: row, index }"
    >
    <tr :key="index">
      <td v-for="col in columns" :key="index + '-' + col" class="log-column">
        <div class="log-column" :style="`width: ${col.width}; min-width: ${col.minWidth}`" @click="expand(row.id)">
          {{ expanded(row.id) ? row.data[col.key] : row.data[col.key].slice(0, 100) }}
        </div>
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
        {key: "asctime", width: "calc(20%)", minWidth: "200px"},
        {key: "levelname", width: "calc(10%)", minWidth: "50px"},
        {key: "msg", width: "calc(70%)"},
      ],
      logUpdateTask: null,
      expandedItems: {},
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
.log-column {
  white-space: break-spaces;
  word-break: break-all;
}
</style>
