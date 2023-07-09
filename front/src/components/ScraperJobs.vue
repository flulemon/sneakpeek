<template>
  <q-table :rows="rows" :columns="columns"  class="full-height" title="Scraper jobs"
           :rows-per-page-options="[0]" :loading="loading" virtual-scroll hide-bottom>
    <template v-slot:body-cell-status="props">
      <q-td :props="props">
        <scraper-job-status-chip :value="props.value" size="sm" />
      </q-td>
    </template>
    <template v-slot:body-cell-priority="props">
      <q-td :props="props">
        <priority-chip :value="props.value" size="sm" />
      </q-td>
    </template>
    <template v-slot:body-cell-timeline="props">
      <q-td :props="props">
        <div class="column">
          <div class="row" v-if="props.value.status == 'pending'">
            <div class="text-weight-bold">Created:&nbsp;</div>
            <div>{{ formatDate(props.value.created_at) }} ({{getRelativeDate(props.value.created_at)}})</div>
          </div>
          <div v-else-if="props.value.status == 'started'" class="column">
            <div class="row">
              <div class="text-weight-bold">Started:&nbsp;</div>
              <div>{{ formatDate(props.value.started_at) }} ({{getRelativeDate(props.value.started_at)}})</div>
            </div>
            <div class="row">
              <div class="text-weight-bold">Last active:&nbsp;</div>
              <div>{{ formatDate(props.value.last_active_at) }} ({{getRelativeDate(props.value.last_active_at)}})</div>
            </div>
          </div>
          <div class="row" v-else>
            <div class="text-weight-bold">Finished:&nbsp;</div>
            <div>{{ formatDate(props.value.finished_at) }} ({{getRelativeDate(props.value.finished_at)}})</div>
          </div>
        </div>
      </q-td>
    </template>
    <template v-slot:body-cell-result="props">
      <q-td :props="props">
        <pre class="job-result">{{ formatResult(props.value) }}</pre>
      </q-td>
    </template>
  </q-table>
</template>

<script>
import { date } from 'quasar';
import { getScraperJobs } from "../api.js";
import PriorityChip from './PriorityChip.vue';
import ScraperJobStatusChip from './ScraperJobStatusChip.vue';

export default {
  components: { ScraperJobStatusChip, PriorityChip },
  name: 'ScraperRuns',
  props: ['id'],
  data() {
    return {
      loading: false,
      error: false,
      rows: [],
      columns: [
        { name: "id", label: "ID", field: "id", align: "left" },
        { name: "status", label: "Status", field: "status", align: "center" },
        { name: "priority", label: "Priority", field: "priority", align: "center" },
        { name: "timeline", label: "Timeline", field: row => row, align: "center" },
        { name: "result", label: "Result", field: "result", align: "center" },
      ],
      loader: null,
      loadingInBackground: false,
    }
  },
  created() {
    this.loading = true;
    this.loadJobs()
      .catch((error => this.error = error))
      .finally(() => this.loading = false);
    this.loadingInBackground = true;
    this.loadJobsInBackground(1000);
  },
  unmounted() {
    this.loadingInBackground = false;
  },
  methods: {
    convertToUserTz(value) {
      const parsed = date.extractDate(value, "YYYY-MM-DDTHH:mm:ss.SSSSSS")
      const formatted = date.formatDate(parsed, "YYYY-MM-DD HH:mm:ss.SSS")
      return new Date(`${formatted} UTC`);
    },
    formatDate(value) {
      const converted = this.convertToUserTz(value);
      return date.formatDate(converted, "YYYY-MM-DD HH:mm");
    },
    formatResult(value) {
      try {
        const parsed = JSON.parse(value);
        return JSON.stringify(parsed, null, 2);
      } catch (e) {
          return value;
      }
    },
    getRelativeDate(value) {
      const now = new Date();
      const parsed = this.convertToUserTz(value);

      const yearsDiff = date.getDateDiff(now, parsed, 'years');
      if (yearsDiff > 1) {
        return `${yearsDiff} years ago`;
      }
      const monthsDiff = date.getDateDiff(now, parsed, 'months');
      if (monthsDiff > 1) {
        return `${monthsDiff} months ago`;
      }
      const daysDiff = date.getDateDiff(now, parsed, 'days');
      if (daysDiff > 1) {
        return `${daysDiff} days ago`;
      }
      const hoursDiff = date.getDateDiff(now, parsed, 'hours');
      if (hoursDiff > 1) {
        return `${hoursDiff} hours ago`;
      }
      const minutesDiff = date.getDateDiff(now, parsed, 'minutes');
      if (minutesDiff >= 1) {
        return `${minutesDiff} minute${minutesDiff > 1 ? 's' : ''} ago`;
      }
      const secondsDiff = date.getDateDiff(now, parsed, 'seconds');
      return `${secondsDiff} seconds ago`;
    },
    loadJobs() {
      return getScraperJobs(this.id).then((data) => this.rows = data);
    },
    loadJobsInBackground() {
      if (!this.loadingInBackground) {
        return;
      }
      this.loadJobs();
      setTimeout(this.loadJobsInBackground, 1000);
    }
  }
}
</script>
<style scoped>
.job-result {
  max-width: 400px;
  text-wrap: wrap;
  text-align: start;
}
</style>
