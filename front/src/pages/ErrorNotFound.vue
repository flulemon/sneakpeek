<template>
  <div class="fullscreen bg-gray text-white text-center q-pa-md flex flex-center">
    <div>
      <div style="font-size: 30vh">
        404
      </div>

      <div class="text-h2" style="opacity:.4">
        Oops. Nothing is here...
      </div>

      <q-btn class="q-mt-xl" flat text-color="" unelevated to="/" label="Go Home" no-caps/>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'ErrorNotFound'
})
</script>
