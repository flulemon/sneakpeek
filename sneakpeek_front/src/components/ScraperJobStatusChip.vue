<template>
  <q-chip :color="color" text-color="white" :label="capitalize(this.value)" v-bind="$attrs"  />
</template>
<script>
import { format } from 'quasar';
const { capitalize } = format;

export default {
  name: "ScraperRunStatusChip",
  props: ["value"],
  data() {
    return {
      statusToColor: {
        "pending": "secondary",
        "started": "warning",
        "succeeded": "positive",
      }
    };
  },
  computed: {
    color() {
      if (this.value in this.statusToColor) {
        return this.statusToColor[this.value];
      }
      return "negative";
    }
  },
  methods: {
    capitalize,
  }
}
</script>
