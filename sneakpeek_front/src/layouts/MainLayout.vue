<template>
  <q-layout view="lHh Lpr lff" container style="height: 100vh" class="shadow-2">
    <q-drawer show-if-above :width="250" :breakpoint="500" :mini="mini" v-model="drawer"
              :class="$q.dark.isActive ? 'bg-black' : 'bg-grey-5'">
      <q-list padding style="height: calc(100vh - 10px)" class="column"
              :class="$q.dark.isActive ? 'text-white': 'text-black'">
        <q-item :to="$router.resolve({name: 'ScrapersPage'})" :focues="false" manual-focus
                :class="$q.dark.isActive ? 'text-white': 'text-black'">
          <q-item-section avatar>
            <q-icon>
              <svg class="img-fluid" id="outputsvg" xmlns="http://www.w3.org/2000/svg"

                viewBox="0 0 2000 2000">
                <g id="l4go2u76yFZO1yZMGfeo1oM"  style="transform: none;">
                  <g style="transform: none;">
                    <path id="pUHK4cYg3"
                      d="M117 1903 c-4 -3 -7 -159 -7 -345 l0 -338 46 0 c29 0 190 43 441 116 l395 117 413 -122 c227 -66 424 -121 439 -121 l26 0 0 350 0 350 -873 0 c-481 0 -877 -3 -880 -7z"></path>
                    <path id="pMO2rLAZ8"
                      d="M662 1210 c-18 -11 -38 -31 -44 -45 -10 -23 -16 -25 -83 -25 -95 0 -107 -10 -103 -80 l3 -55 245 0 245 0 3 73 3 73 -39 40 c-39 39 -40 39 -118 39 -61 0 -86 -5 -112 -20z"></path>
                    <path id="pm3wH3Llu"
                      d="M1289 1213 c-15 -9 -34 -29 -43 -45 -16 -26 -21 -28 -81 -28 -35 0 -75 -4 -89 -10 -23 -8 -26 -15 -26 -58 0 -26 5 -53 12 -60 9 -9 77 -12 243 -12 166 0 234 3 243 12 17 17 15 104 -5 145 -25 54 -65 73 -153 73 -52 0 -83 -6 -101 -17z"></path>
                    <path id="pmed2ttMB"
                      d="M184 896 c-3 -7 -4 -35 -2 -62 l3 -49 102 -3 103 -3 15 -52 c8 -29 52 -182 99 -342 l83 -290 31 -3 c25 -3 63 19 206 114 l176 117 168 -66 c92 -37 181 -67 198 -67 l31 0 109 293 109 292 85 3 c46 2 90 8 97 14 16 13 17 90 1 106 -19 19 -1607 17 -1614 -2z"></path>
                  </g>
                </g>
                <g id="l2iB71gug0KQl2CIfZpzhLk" fill="rgba(0,0,0,0)" style="transform: none;">
                  <g style="transform: none;">
                    <path id="pX8JVs27A"
                      d="M0 1000 l0 -1000 1000 0 1000 0 0 1000 0 1000 -1000 0 -1000 0 0 -1000z m1840 561 l0 -319 -77 23 c-43 12 -234 68 -425 124 l-346 102 -410 -120 c-226 -67 -418 -121 -426 -121 -14 0 -16 35 -16 308 0 170 3 312 7 315 3 4 386 7 850 7 l843 0 0 -319z m-978 -400 c35 -36 39 -44 36 -83 l-3 -43 -215 0 -215 0 -3 24 c-6 38 22 51 103 51 67 0 73 2 83 25 18 38 69 65 126 65 43 0 53 -4 88 -39z m604 20 c31 -19 64 -74 64 -108 0 -40 -16 -43 -225 -43 -208 0 -225 3 -225 42 0 25 39 38 115 38 60 0 65 2 81 28 9 16 28 36 43 45 36 22 109 21 147 -2z m305 -317 c9 -11 10 -20 2 -32 -8 -13 -31 -18 -99 -22 l-88 -5 -108 -285 c-59 -157 -108 -288 -110 -293 -2 -4 -82 24 -178 63 -96 39 -182 72 -190 72 -8 1 -97 -53 -198 -120 -117 -79 -184 -118 -187 -110 -2 7 -38 132 -80 278 -42 146 -85 295 -96 332 l-20 67 -102 3 c-89 3 -102 5 -105 21 -10 49 -47 47 776 47 690 0 771 -2 783 -16z"></path>
                  </g>
                </g>
              </svg>
            </q-icon>
          </q-item-section>
          <q-item-section class="text-h5">Sneakpeeker</q-item-section>
        </q-item>
        <q-separator spaced :color="$q.dark.isActive ? 'white': 'white'" />
        <q-item clickable v-ripple :to="$router.resolve({name: 'ScrapersPage'})"
                :class="$q.dark.isActive ? 'text-white': 'text-black'">
          <q-item-section avatar>
            <q-icon name="dashboard" />
          </q-item-section>
          <q-item-section>
            Scrapers
          </q-item-section>
        </q-item>
        <q-item clickable v-ripple :to="$router.resolve({name: 'NewScraperPage'})"
                :class="$q.dark.isActive ? 'text-white': 'text-black'">
          <q-item-section avatar>
            <q-icon name="fa-solid fa-plus" />
          </q-item-section>
          <q-item-section>
            New scraper
          </q-item-section>
        </q-item>
        <q-space vertical />
        <q-item clickable v-ripple href="https://github.com/flulemon/sneakpeek">
          <q-item-section avatar>
            <q-icon name="fa-brands fa-github" />
          </q-item-section>
          <q-item-section>
            Github
          </q-item-section>
        </q-item>
        <q-item clickable v-ripple href="https://github.com/flulemon/sneakpeek">
          <q-item-section avatar>
            <q-icon name="fa-solid fa-code" />
          </q-item-section>
          <q-item-section>
            Documentation
          </q-item-section>
        </q-item>
        <q-item clickable v-ripple @click="$q.dark.toggle()">
          <q-item-section avatar>
            <q-icon :name="'fa-solid ' + ($q.dark.isActive ? 'fa-moon' : 'fa-sun')" />
          </q-item-section>
          <q-item-section>
            {{ $q.dark.isActive ? 'Dark' : 'Light' }} mode
          </q-item-section>
        </q-item>
      </q-list>
      <div class="absolute" style="top: 100px; right: -12px">
          <q-btn dense round unelevated  @click="mini = !mini" size="sm"
            :color="$q.dark.isActive ? 'grey-8': 'grey-8'"
            :icon="mini ? 'fa-solid fa-chevron-right' : 'fa-solid fa-chevron-left'"/>
        </div>
    </q-drawer>
    <q-page-container :class="$q.dark.isActive ? 'bg-grey-9' : 'bg-grey-2'">
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script>
import { defineComponent, ref } from 'vue';

export default defineComponent({
  name: 'MainLayout',
  setup () {
    const drawer = ref(false)
    const mini = ref(false)
    return {
      drawer,
      mini,
    }
  }
})
</script>
