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
      Scientists do not typically think in terms of a "right answer." Instead, they use data to describe how much confidence they have in a particular result. We hope this Data Story has given you a better understanding of how to do this.
    </p>
    <p>
      The current accepted age of the universe, measured using several independent methods, is about 14 billion years.
    </p>
    <p>
      Science is always moving forward and there is always more humans can learn about our universe. Follow NASA to learn what new discoveries are being made by HST's successor, the James Webb Space Telescope!
    </p>
  </div>
  </scaffold-alert>
</template>

<script setup>
</script>
