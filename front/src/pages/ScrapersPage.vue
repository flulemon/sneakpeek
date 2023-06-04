<template>
  <q-page class="flex flex-center" style="width: 100%;">
    <q-table :rows="rows" :columns="columns" row-key="id"
             style="width: 100%; height: 100vh;" virtual-scroll hide-bottom
             :loading="loading" :rows-per-page-options="[0]" :filter="filter">
      <template v-slot:top>
        <div class="text-h6">Scrapers</div>
        <q-space />
        <q-input dense color="primary" style="width: 300px;"
                 v-model="filter" placeholder="Search..." clearable>
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>

      <template v-slot:body-cell-name="props">
        <q-td :props="props">
          <q-item clickable v-ripple :href="$router.resolve({ name: 'ScraperPage', params: { id: props.value.id } }).href">
            <q-item-section>
              {{ props.value.name }}
            </q-item-section>
          </q-item>
        </q-td>
      </template>


      <template v-slot:body-cell-priority="props">
        <q-td :props="props">
          <priority-chip :value="props.value" size="sm" />
        </q-td>
      </template>

      <template v-slot:body-cell-schedule="props">
        <q-td :props="props">
          <schedule-chip size="sm" color="primary" text-color="white" :value="props.value" />
        </q-td>
      </template>

      <template v-slot:body-cell-actions="props">
        <q-td :props="props">
            <q-btn flat size="sm"
                :to="$router.resolve({ name: 'ScraperPage', params: { id: props.value.id } })">
              <q-icon name="fa-solid fa-edit" class="q-mr-sm" />
              Edit
            </q-btn>
        </q-td>
      </template>

    </q-table>
  </q-page>
</template>

<script>
import { getScrapers } from "../api.js";
import PriorityChip from '../components/PriorityChip.vue';
import ScheduleChip from '../components/ScheduleChip.vue';

export default {
  components: { PriorityChip, ScheduleChip },
  name: 'ScrapersPage',
  data() {
    return {
      loading: false,
      error: false,
      columns: [
        { name: 'id', label: 'ID', field: 'id', align: 'left' },
        { name: 'name', label: 'Name', field: row => row, align: 'left'},
        { name: 'schedule', label: 'Schedule', field: 'schedule', align: 'center' },
        { name: 'priority', label: 'Priority', field: 'schedule_priority', align: 'center' },
        { name: 'actions', label: 'Actions', field: row => row, align: 'right' },
      ],
      rows: [],
      filter: '',
    }
  },
  created() {
    this.filter = this.$route.query.f || '';
    this.loading = true;
    getScrapers()
      .then((data) => this.rows = data)
      .catch((error => this.error = error))
      .finally(() => this.loading = false);
  },
  watch: {
    filter(value) {
      if (value) {
        this.$router.replace({query: { f: value }});
      } else {
        this.$router.replace({query: { }});
      }
    }
  }
}
</script>
