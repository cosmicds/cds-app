<template>
  <scaffold-alert
    color="info"
    class="mb-4 mx-auto"
    max-width="800"
    elevation="6"
    title-text="Angular Size Measurement"
    @back="back_callback()"
    @next="next_callback()"
    :can-advance="can_advance"
  >
    <template #before-next>
      Click the <v-btn icon dark x-small disabled class="mx-1 black--text" elevation="2" style="background-color: #00E676;"><v-icon style="color:black!important;">mdi-ruler</v-icon></v-btn>  icon.
    </template>

    <div
      class="mb-4"
    >
      <p>
        Zoom in or out so your entire galaxy is framed within the viewer.
      </p>    
      <p>
        Adjust the brightness using the <v-icon>mdi-brightness-6</v-icon> slider if needed.
      </p>      
      <p>
        Click the <v-btn icon dark x-small disabled class="mx-1 black--text" elevation="2" style="background-color: #00E676;"><v-icon style="color:black!important;">mdi-ruler</v-icon></v-btn>  icon to activate the angular size measuring tool.
      </p>
    </div>
  </scaffold-alert>
</template>
<script>
</script>