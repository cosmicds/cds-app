<template>
  <scaffold-alert
    title-text="Professional Data"
    @back="back_callback()"
    @next="next_callback()"
    :can-advance="can_advance"
  >
    <template #before-next>
      Choose a response.
    </template>
    <div
      class="mb-4"
    >
    <p>
      Edwin Hubble's own data from 1929 is shown in {{ state_view.hubble1929_color }}. (As before, your class's data is shown in {{ state_view.class_color }}).
    </p>

    <p>
      Does your class's age estimate agree with Hubble's age estimate? 
    </p>
    <p>
      Hint: Remember that we estimated the age of the universe from the slope of the best-fit line to our data, so we can compare age estimates from two different data sets by comparing the slopes. 
    </p>

    <v-container
        class="px-0"
        fluid
      >
        <mc-radiogroup
          :radio-options="[
            'Yes',
            'No',
            'I\'m not sure',
          ]"
          :feedbacks="[
            'The slope of the line is related to the age measurement from this data. Are the slopes the same?',
            'Correct. The best fit lines for our data and Edwin Hubble\'s data have very different slopes, so they have different ages.',
            'The slope of the line is related to the age measurement from this data. Are the slopes the same?']"
          :incorrect-answers="[0]"
          :correct-answers="[1]"
          :neutral-answers="[2]"
          :score-tag="state_view.score_tag"
          @mc-emit="mc_callback($event)"
          :initialization="state_view.mc_score"
        >
        <!-- @mc-initialize-response="mc_initialize_response_callback($event)"
          @mc-score="mc_score_callback($event)" -->
        </mc-radiogroup>
      </v-container>
    </div>
  </scaffold-alert>
</template>

<script>
module.exports = {
  data() {
    return {
    };
  },
  
  methods: {
    log(val) {
      console.log(val);
    },
  }
};
</script>
