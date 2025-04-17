<template>
  <scaffold-alert
  @back="back_callback()"
  @next="next_callback()"
  :can-advance="can_advance"
  >
    <div
      class="mb-4"
    >
    <p>
      Thank you so much for using the Hubble Data Story. Please complete this final survey. Your feedback will help us improve this and future Data Stories for other students.
    </p>
            <v-btn
              block
              class="black--text"
              color="accent"
              elevation="2"
              target="_blank"
              href='https://harvard.az1.qualtrics.com/jfe/form/SV_da5atALEUw7gMjI'
            >
              <b>survey</b>
            </v-btn>
    </div>
  </scaffold-alert>
</template>

<script setup>
</script>
