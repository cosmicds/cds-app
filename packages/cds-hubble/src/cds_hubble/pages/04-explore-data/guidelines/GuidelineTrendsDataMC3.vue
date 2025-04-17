<template>
  <scaffold-alert
    title-text="Trends in the Data"
    @back="back_callback()"
    @next="next_callback()"
    :can-advance="can_advance"
  >
    <template #before-next>
      Choose a response.
    </template>

    <div>
      <p>
        Now with a larger data set, do you see a trend? Is there a relationship between the velocity and distance of the galaxies?
      </p>
      <v-container
        class="px-0"
        fluid
      >
        <mc-radiogroup
          :radio-options="[
            'Yes, I see a trend.',
            'No, I don\'t see a trend.',
            'I can\'t tell if there\'s a trend.',
            'The larger data set made my trend harder to see.',
          ]"
          :feedbacks="[
            'Cool, right? When there is a lot of random variation in properties being measured (like galaxy sizes) and you have a small sample, whether you saw a trend or not depends on the galaxies you happened to pick. You need a large enough sample to have confidence in the overall trend.',
            'Try talking to a neighbor or your instructor. Even with a noisy dataset, you should be able to make out some sort of trend',
            'Try talking to a neighbor or your instructor. Even with a noisy dataset, you should be able to make out some sort of trend',
            'This can happen when there is a lot of random variation in properties being measured (like galaxy sizes). With a small sample, whether you saw a strong trend or not depends on the galaxies you happened to pick. You need a large enough sample to have confidence in the overall trend.',
          ]"
          :correct-answers="[]"
          :neutral-answers='[0,1,2,3]'
          :score-tag="state_view.score_tag"
          @mc-emit="mc_callback($event)"
          :initialization="state_view.mc_score"
        >
        </mc-radiogroup>
        <v-btn
          block
          color="deep-orange darken-2"
          @click="
            define_trend = !define_trend
          "
        >
          What is a trend?
        </v-btn>
        <v-alert
          class="mt-4 trend-alert" 
          v-if="define_trend"
          dense
          color="info darken-1"
        >
          A trend is a pattern in data (for example, an upward <v-icon>mdi-arrow-top-right-bottom-left-bold</v-icon> or downward <v-icon>mdi-arrow-top-left-bottom-right-bold</v-icon> line). 
        </v-alert>
      </v-container>
    </div>
  </scaffold-alert>
</template>

<script>
module.exports = {
  
  data() {
    return {
      define_trend: false,
    };
  },
};
</script>