<template>
  <v-card
    id="slideshow-root"
    elevation="6"
  >
    <v-toolbar
      ref="toolbar"
      color="warning"
      dense
      dark
    >
      <v-toolbar-title
        class="text-h6 text-uppercase font-weight-regular"
      >
        {{ titles[step] }}
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <speech-synthesizer
        ref="synth"
        :root="getRoot"
        :element-filter="(element) => {
          // There's some annoying behavior with when elements lose visibility when changing
          // window items. Rather than doing some crazy shenanigans to wait the right amount of time,
          // we just explicitly filter out elements that aren't descendants of the toolbar
          // or the current window item
          if (this.$refs.toolbar.$el.contains(element)) { return true; }
          const currentWindowItem = this.$el.querySelector('.v-window-item--active');
          return currentWindowItem?.contains(element) ?? false;
        }"
        :autospeak-on-change="step"
        :selectors="['div.v-toolbar__title.text-h6', 'h3', 'p']"
        :options="speech"
      />
    </v-toolbar>

    <v-window
      style="height: calc(100vh - 250px); overflow: auto;"
      v-model="step"
    >

      <v-window-item :value="0" 
        class="no-transition"
      >
        <v-card-text
        >
          
            <v-row>
              <v-col cols="12" lg="5">
                <p>
                  Humans have always looked to the sky and wondered how we and our universe came to be. 
                </p>
                <p>
                  In this <strong>Cosmic Data Story</strong>, you will use authentic astronomical data to investigate the mysteries of our Universe. In particular, you will be answering these questions:
                </p>
                <v-card
                  class="justify-center pa-2 mx-12 my-8"
                  color="primary"
                  style="font-weight:600;"
                  dark
                >
                  <p
                    class="my-3 text-center"
                  >
                    Has the universe always existed?
                  </p>
                  <p
                    class="my-3 text-center"
                  >
                    If not, how long ago did it form?
                  </p>
                </v-card>
              </v-col>
              <v-col cols="12" lg="7" align="center">
                <v-img
                  :lazy-src="`${image_location}/MilkyWayOverMountainsNASASTScILevay.jpg`"
                  :src="`${image_location}/MilkyWayOverMountainsNASASTScILevay.jpg`"
                  alt="Colorful image of our Milky Way galaxy in the sky over a dark silhouette of mountains on the horizon."
                  max-height = "550px"
                  contain
                ></v-img>
                <div
                  class="text-center mt-2 grey--text"
                  style="width: 75%;"
                >
                  Our Milky Way galaxy over a mountain range. (Credit: NASA and STScI)
                </div>
              </v-col>
            </v-row>
          
        </v-card-text>
      </v-window-item>

      <v-window-item :value="1" 
        class="no-transition"
      >
        <v-card-text
        >
          
            <v-row>
              <v-col cols="12" lg="5">
                
                <p>
                  When scientists collect data to answer questions no one has answered yet, there is no answer key in the back of some book. So, as you explore this data story, you will learn how to <strong>evaluate the reliability</strong> of your results. Are the data really good enough to support a conclusion? <strong>How can you know?</strong> 
                </p>
                <p>
                  Just as scientists constantly must, you'll <strong>determine what can be concluded</strong> from the data at-hand, and <strong>how much confidence</strong> you can have in your conclusions.
                </p>
                <p>
                  Let's get started.
                </p>
              </v-col>
              <v-col cols="12" lg="7">
                <v-row no-gutter>
                  <v-col cols="6" lg="12">
                    <v-img
                      position="center center"
                      :lazy-src="`${image_location}/HST-SM4.jpeg`"
                      :src="`${image_location}/HST-SM4.jpeg`"  
                      alt="The Hubble Space Telescope against a dark background"
                      max-height = "250"
                      contain
                    ></v-img>
                  </v-col>
                  <v-col cols="6" lg="12">
                    <v-img
                      :lazy-src="`${image_location}/EdwinHubble.jpg`"
                      :src="`${image_location}/EdwinHubble.jpg`"
                      alt="Astronomer Edwin Hubble holding an image of the Andromeda Galaxy"
                      max-height = "250"
                      contain
                    ></v-img>
                  </v-col>
                </v-row>
                <div
                  class="text-center mt-2 grey--text"
                  style="width: 100%;"
                >
                  The Hubble Space Telescope and Edwin Hubble, the astronomer it was named for. Hubble holds an image of the Andromeda Galaxy, for which the earliest recorded observation was made in 964 AD by Iranian scholar al-Sufi.
                </div>
              </v-col>
            </v-row>
          
        </v-card-text>
      </v-window-item>
      
      <v-window-item :value="2" 
        class="no-transition"
       >
        <v-card-text>
          
            <v-row>
              <v-col cols="12" lg="5">
                <p>
                  Imagine that you are an astronomer living in the <strong>early 1900s</strong>. You and your colleagues around the world, including Albert Einstein, would agree that the <strong>universe is unchanging</strong> and <strong>everlasting.</strong> In other words, you expect that the universe always has been and will be the way it is the way you see it now. This picture of an unchanging universe had rarely been questioned throughout human history, thanks in large part to <strong>Aristotle</strong>, who embraced perfection and permanence. 
                </p>
              </v-col>
              <v-col cols="12" lg="7">
                <v-row>
                  <v-col cols="12">
                    <v-img
                      :lazy-src="`${image_location}/Astronomer_Edward_Charles_Pickering's_Harvard_computers.jpg`"
                      :src="`${image_location}/Astronomer_Edward_Charles_Pickering's_Harvard_computers.jpg`"
                      alt="Eight women astronomers, wearing late 1800s clothing and hairstyles, are sitting or standing in a room. Some are observing astronomical images with magnifying glasses. Some are writing in notebooks."
                      max-height="300"
                      contain
                    ></v-img>
                  </v-col>
                  <div
                    class="text-center grey--text mb-5"
                    style="width: 100%;"
                  >
                    Women astronomers at Harvard College Observatory in 1892, including Henrietta Leavitt (third from left), Williamina Fleming (standing), and Annie Jump Cannon (far right).
                  </div>
                </v-row>
                <v-row no-gutters>
                  <v-col cols="6">
                    <v-img
                      class="mr-5"
                      position="center right"
                      :lazy-src="`${image_location}/Einstein_1921_by_F_Schmutzer_-_restorationCropped.png`"
                      :src="`${image_location}/Einstein_1921_by_F_Schmutzer_-_restorationCropped.png`"
                      alt="Portrait of Albert Einstein"
                      contain
                      max-height="150"
                    ></v-img>
                  </v-col>
                  <v-col cols="6">
                    <v-img
                      position="center left"
                      :lazy-src="`${image_location}/AristotleSchoolOfAthensCutoutZoom.png`"
                      :src="`${image_location}/AristotleSchoolOfAthensCutoutZoom.png`"
                      alt="Cutout showing a small portion of a much larger, colorful paiting by Raphael depicting Aristotle wearing a blue robe."
                      contain
                      max-height="150"
                    ></v-img>
                  </v-col>
                  <div
                    class="text-center mt-3 grey--text"
                    style="width: 100%;"
                  >
                    Left: Albert Einstein in 1921. Right: Aristotle, depicted in “The School of Athens,” painted by Raphael for the walls of the Vatican between 1509 and 1511. Both believed in an unchanging universe. 
                  </div>
                </v-row>
              </v-col>
            </v-row>
          
        </v-card-text>
      </v-window-item>

      <v-window-item :value="3" 
        class="no-transition"
      >
        <v-card-text>
          
            <v-row>
              <v-col>
                <div
                  style="min-height: 120px;"
                >
                  <p>
                    The frame below provides an <strong>interactive view</strong> of the night sky, using images from real observations.
                  </p>
                  <p>
                    The brighter band you see going diagonally across the frame (before you try the controls) is caused by stars and dust in our home galaxy, called the <strong>Milky Way.</strong>
                  </p>
                  <p>
                    You can explore this view and see what is in the night sky, as astronomers have been doing for centuries. <strong>Pan</strong> (click and drag) and <strong>zoom</strong> (scroll in and out) to see parts of the sky beyond this view.
                  </p>
                </div>
                <div
                  class="mb-2 mx-4"
                >    
                  <v-row>
                    <v-col
                      cols="8"
                      offset-lg="1"
                    >
                      <v-row>
                        <v-col>
                          <jupyter-widget :widget="exploration_tool" />
                          <div
                            class="text-center grey--text mt-2"
                            style="width: 100%;"
                          >
                            <i>Interactive view provided by WorldWide Telescope</i>
                          </div>
                        </v-col>
                      </v-row>
                      
                    </v-col>
                    <v-col 
                      cols="4" 
                      lg="3" 
                      style="gap:1rem;"
                    >
                      <v-row class="justify-start" style="gap:1em;">
                        <v-chip
                          label
                          outlined
                        >
                          Pan
                        </v-chip>|
                        <div class="pt-2"
                        >
                          <strong>click + drag</strong><br>
                          (or use <strong class="codeFont">I-J-K-L</strong> keys)
                        </div>
                      </v-row>
                      <v-row>
                      <v-row class="justify-start" style="gap:1em;">
                          <v-chip
                            label
                            outlined
                          >
                            Zoom
                        </v-chip>|
                        <div class="pt-2"
                        >
                          <strong>scroll in and out</strong><br>
                          (or use <strong class="codeFont">Z-X</strong> keys)
                        </div>
                      </v-row>
                      </v-row>
                    </v-col>
                  </v-row>
                </div>
              </v-col>
            </v-row>
            <v-snackbar
              v-model="timerComplete[0]"
              :timeout="500000"
              transition="fab-transition"
              top
              right
              color="cyan lighten-2"
              class="pa-4 black--text"
              style="font-size: 1.25rem;"
              multi-line
              elevation="24"
            >
              There is a lot more to explore, so don't linger here for too long!
              <v-btn
                color="accent"
                class="mx-4 black--text"
                @click="() => {
                  timerComplete[0] = false;
                  set_step(step+1);
                }"
              >
                move on
              </v-btn>
            </v-snackbar>
                                                
        </v-card-text>
      </v-window-item>

      <v-window-item :value="4" 
        class="no-transition"
      >
        <v-card-text>
          
            <v-row>
              <v-col>
                <div
                  style="min-height: 120px;"
                >
                  <p>
                    As you explore the cosmic sky, you may see stars and fuzzy blobs called <strong>nebulae</strong>. In the 1700's, French astronomer Charles Messier cataloged as many nebulae as he could find. They are known as Messier Objects and are identified by their catalog number. For example, M13 represents the 13th Messier Object in the catalog.
                  </p>
                  <p>
                    Click on the buttons to the right to <strong>view some Messier Objects</strong>. (Fun fact: “nebula” means “cloud” or “fog” in Latin.)
                  </p>
                </div>
                <div
                  class="mb-2 mx-4"
                >    
                  <v-row>
                    <v-col
                      cols="8"
                      offset-lg="1"
                    >
                      <jupyter-widget :widget="exploration_tool1" />
                      <div
                        class="text-center grey--text mt-2"
                        style="width: 100%;"
                      >
                        <i>Interactive view provided by WorldWide Telescope</i>
                      </div>
                    </v-col>
                    <v-col
                      cols="4"
                      lg="2"
                    >
                      <v-row
                        justify="space-between"
                      >
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn 
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 83.63,
                                dec: 22.014,
                                fov: 350, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M1';
                              startTimerIfNeeded(1);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M1'"
                          >
                            M1 
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 250.4,
                                dec: 36.46,
                                fov: 700, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M13';
                              startTimerIfNeeded(1);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M13'"
                          >
                            M13
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 10.63,
                                dec: 41.27,
                                fov: 6000, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M31';
                              startTimerIfNeeded(1);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M31'"
                          >
                            M31 
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 83.82,
                                dec: -5.39,
                                fov:7500, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M42';
                              startTimerIfNeeded(1);  
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M42'"
                          >
                            M42
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 202.47,
                                dec: 47.195,
                                fov: 700, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M51';
                              startTimerIfNeeded(1);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M51'"
                          >
                            M51
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 1,
                                ra: 148.97,
                                dec: 69.68,
                                fov: 400, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M82';
                              startTimerIfNeeded(1);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M82'"
                          >
                            M82
                          </v-btn>
                        </v-col>
                      </v-row>
                    </v-col>
                  </v-row>
                </div>
              </v-col>
            </v-row>
            <v-snackbar
              v-model="timerComplete[1]"
              :timeout="500000"
              transition="fab-transition"
              top
              right
              color="cyan lighten-2"
              class="pa-4 black--text"
              style="font-size: 1.25rem;"
              multi-line
              elevation="24"
            >
              There is a lot more to explore, so don't linger here for too long!
              <v-btn
                color="accent"
                class="mx-4 black--text"
                @click="() => {
                  timerComplete[1] = false;
                  set_step(step+1);
                }"
              >
                move on
              </v-btn>
            </v-snackbar>
          
        </v-card-text>
      </v-window-item> 

      <v-window-item :value="5" 
        class="no-transition"
      >
        <v-card-text>
          
            <v-row>
              <v-col>
                <div
                  style="min-height: 120px;"
                >
                  <p>
                    <strong>M31</strong> and <strong>M51</strong> are examples of a particular type of nebula that interested astronomers in the early 1900s. They were known as <strong>spiral nebulae</strong> because of their distinctive spiral shape. In 1920, there was a Great Debate between astronomers Harlow Shapley and Heber Curtis questioning whether the spiral nebulae were perhaps young solar systems being born within our Milky Way galaxy or were "island universes” beyond it.
                  </p>
                  <p>
                    While you view these spiral nebulae, ponder what you would need to know to determine if they are within the Milky Way or beyond it. (Don't worry if you don't know. You will learn in this Data Story.) 
                  </p>
                </div>
                <div
                  class="mb-2 mx-4"
                >    
                  <v-row>
                    <v-col
                      cols="8"
                      offset-lg="1"
                    >
                      <jupyter-widget :widget="exploration_tool2" />
                      <div
                        class="text-center grey--text mt-2"
                        style="width: 100%;"
                      >
                        <i>Interactive view provided by WorldWide Telescope</i>
                      </div>
                    </v-col>
                    <v-col
                      cols="4"
                      lg="2"
                    >
                      <v-row
                        justify="space-between"
                      >
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            :disabled=true
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M1'"
                          >
                            M1
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            :disabled=true
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M13'"
                          >
                            M13
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 2,
                                ra: 10.63,
                                dec: 41.27,
                                fov: 6000, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M31';
                              startTimerIfNeeded(2);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M31'"
                          >
                            M31
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            :disabled=true
                            color="warning"
                            width="100%"
                            class="mx-2"
                          >
                            M42
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            @click="() => {
                              go_to_location({
                                index: 2,
                                ra: 202.47,
                                dec: 47.195,
                                fov: 700, // optional, in arcseconds, default is 90
                                instant: false, // also optional, false by default
                              });
                              target = 'M51';
                              startTimerIfNeeded(2);
                            }"
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :outlined="target === 'M51'"
                          >
                            M51
                          </v-btn>
                        </v-col>
                        <v-col
                          cols="12"
                          lg="6"
                        >
                          <v-btn
                            color="warning"
                            width="100%"
                            class="mx-2"
                            :disabled=true
                          >
                            M82
                          </v-btn>
                        </v-col>
                      </v-row>
                    </v-col>
                  </v-row>
                </div>
              </v-col>
            </v-row>
            <v-snackbar
              v-model="timerComplete[2]"
              :timeout="500000"
              transition="fab-transition"
              top
              right
              color="cyan lighten-2"
              class="pa-4 black--text"
              style="font-size: 1.25rem;"
              multi-line
              elevation="24"
            >
              There is a lot more to explore, so don't linger here for too long!
              <v-btn
                color="accent"
                class="mx-4 black--text"
                @click="() => {
                  timerComplete[2] = false;
                  set_step(step+1);
                }"
              >
                move on
              </v-btn>
            </v-snackbar>
             
        </v-card-text>
      </v-window-item>

      <v-window-item :value="6" 
        class="no-transition"
      >
        <v-card-text>
          
            <v-row>
              <v-col>
                <p>
                  Between 1907&#8211;1921, Harvard astronomer <strong>Henrietta Leavitt</strong> observed Cepheid variable stars in a nebula called the Small Magellanic Cloud (SMC). By analyzing changes in the Cepheid stars’ brightness over time, she discovered that <strong>fainter Cepheids vary more slowly than brighter ones</strong>, as shown in her graph below. This important discovery made it possible to determine distances to spiral nebulae and finally resolve the Shapley-Curtis Great Debate: it turned out that spiral nebulae are far beyond the Milky Way and constitute <strong>individual galaxies</strong> in their own right.
                </p>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols= "8">
                <v-row class="pb-3">
                  <v-img
                    :lazy-src="`${image_location}/Leavitt_at_work.jpg`"
                    :src="`${image_location}/Leavitt_at_work.jpg`"
                      alt="Photograph of Henrietta Leavitt writing in a notebook. Several other notes are open neatly around her desk. "
                      max-height = "350"
                      contain
                    ></v-img>
                  <div
                    class="text-center mt-3 grey--text"
                    style="width: 100%;"
                  >
                    Astronomer Henrietta Swan Leavitt
                  </div>
                </v-row>
              </v-col>
              <v-col cols= "4">
                <v-row>
                  <v-img
                    :lazy-src="`${image_location}/Leavitt_Plate.png`"
                    :src="`${image_location}/Leavitt_Plate.png`"
                    alt="Photographic glass plate of the Small Magellenic Cloud. Handwritten markings are scattered around the plate, noting objects of interest."
                    max-height = "200"
                    contain
                  ></v-img>
                  <div
                    class="text-center mb-6 mt-2 grey--text"
                    style="width: 100%;"
                  >
                    Glass plate showing Cepheid variable stars in SMC studied by Leavitt
                  </div>
                </v-row>
                <v-row>
                  <v-img
                    :lazy-src="`${image_location}/HSLeavittHSCr13Fig2_1912.jpeg`"
                    :src="`${image_location}/HSLeavittHSCr13Fig2_1912.jpeg`"
                    alt="A graph depicting stellar magnitude on the y-axis and period in days on the x-axis. Two plots are shown that go from the bottom left to the upper right of the chart."
                    max-height = "200"
                    contain
                  ></v-img>
                  <div
                    class="text-center mt-3 grey--text"
                    style="width: 100%;"
                  >
                    Graph from Leavitt's 1912 paper showing the relationship between period and brightness of Cepheid variables.
                  </div>
                </v-row>
              </v-col>
            </v-row>
          
        </v-card-text>
      </v-window-item>

      <v-window-item :value="7" 
        class="no-transition"
        
      >
        <v-card-text>
          
            <v-row>
              <v-col>
                <p>
                  Around this same time, astronomer <strong>Vesto Slipher</strong> observed spiral nebulae using a spectrograph. Spectrographs can reveal a lot about an object in space, like what the object is made of or how fast it is moving toward or away from the observer.
                </p>
                <p>
                  Recall that the prevailing view in the early 1900s was that the universe is unchanging and eternal. As a result, the dominant expectation was that distant spiral nebulae are either not moving at all, or if they are moving then they are moving randomly.
                </p>
                <p>
                  It’s time for you to collect some of your own data, form conclusions, and compare your conclusions to what Vesto Slipher found.
                </p>
              </v-col>
              <v-col cols="5">
                <v-img
                  :lazy-src="`${image_location}/V.M.Slipher.gif`"
                  :src="`${image_location}/V.M.Slipher.gif`"
                  alt="Portrait of Vesto Slipher"
                  max-height = "400"
                  contain
                ></v-img>
                  <div
                    class="text-center mt-3 grey--text"
                    style="width: 100%;"
                  >
                    Astronomer Vesto Slipher
                  </div>
              </v-col>
            </v-row>
          
        </v-card-text>
      </v-window-item>
    </v-window>

    <v-divider></v-divider>

    <v-card-actions
      class="justify-space-between"
    >
      <v-btn
        :disabled="step === 0"
        class="black--text"
        color="accent"
        depressed
        @click="() => {
          set_step(step-1);
          let options = null;
          if (step === 4) {
            options = {
              index: 1,
              ra: 266.64, // default MW coords
              dec: -28.39,
              fov: 216000, // 60 degrees
              instant: true, // also optional, false by default
            };
          } else {
            options = {
              index: 2,
              ra: 10.63,
              dec: 41.27,
              fov: 6000, // optional, in arcseconds, default is 90
              instant: true, // also optional, false by default
            };
            target = 'M31';
          }
          go_to_location(options)
        }"
      >
        back
      </v-btn>
      <v-spacer></v-spacer>
      <v-item-group
        v-model="step"
        class="text-center"
        mandatory
      >
        <v-item
          v-for="n in length"
          :key="`btn-${n}`"
          v-slot="{ active, toggle }"
        >
          <v-btn
            :input-value="active"
            icon
            @click="toggle; set_step(n-1);"
          >
            <v-icon
              color="info lighten-1"
            >
              mdi-record
            </v-icon>
          </v-btn>
        </v-item>
      </v-item-group>
      <v-spacer></v-spacer>
      <!-- Code to use for disable in button below if step 3 depends on exploring WWT first: -->
      <!-- :disabled="step === length-1 || (step === 3 && !exploration_complete)" -->
      <v-btn
        :disabled="step >= length-1"
        v-if="step < length-1"
        class="black--text"
        color="accent"
        depressed
        @click="() => {
          set_step(step+1);
          let options = null;
          if (step === 4) {
            options = {
              index: 1,
              ra: 266.64, // default MW coords
              dec: -28.39,
              fov: 216000, // 60 degrees
              instant: true, // also optional, false by default
            };
          } else {
            options = {
              index: 2,
              ra: 10.63,
              dec: 41.27,
              fov: 6000, // optional, in arcseconds, default is 90
              instant: true, // also optional, false by default
            };
            target = 'M31';
          }
          go_to_location(options)
        }"
      >
        next
      </v-btn>
      <!-- first button below just being used for testing, delete when using live with students -->
      <v-btn
        v-if="step < length-1 && show_team_interface"
        class="demo-button"
        depressed
        @click="() => {
          slideshow_finished();
          set_step(0);
          // this.$refs.synth.stopSpeaking();
        }"
      >
        jump to Stage 1
      </v-btn>
      <v-btn
        v-if="step >= length-1"
        :disabled="step > length-1"
        color="accent"
        class="black--text"
        depressed
        @click="() => { 
          slideshow_finished();
          set_step(0);
          // this.$refs.synth.stopSpeaking();
        }"
      >
        Stage 1
      </v-btn>
    </v-card-actions>
  </v-card>
</template>


<style>
.no-transition {
  transition: none !important;
}

#slideshow-root .v-card__text{
  padding: 0px 15px 0px;
  /* min-height: 550px;  */
}

#exploration-tool, #exploration-tool2, #exploration-tool3 {
  height: 400px;
}

.v-snack__content {
  padding: 12px 16px;
}
</style>


<script>
module.exports = {
  props: ["continueText"],
  data() {
    return {
      target: '',
      timerDuration: [300000, 180000, 180000],
      timerStarted: [false, false, false],
      timerComplete: [false, false, false],
    };
  },
  methods: {
    getRoot() {
      return this.$el;
    },
    startTimer(number) {
      setTimeout(() => {
        this.$set(this.timerComplete, number, true);
      }, this.timerDuration[number]);
      this.$set(this.timerStarted, number, true);
    },
    startTimerIfNeeded(number) {
      if (!this.timerStarted[number]) {
        this.startTimer(number);
      }
    },
  },

  watch: {
    step(val) {
      if (val > this.max_step) {
        this.set_max_step(val);
      }
      this.target = '';
      if (val >= 3 && val <= 5) {
        const index = val - 3;
        this.$set(this.timerStarted, index, false);
        this.$set(this.timerComplete, index, false);
        this.startTimerIfNeeded(index);
      }
    }
  }
};
</script>

<style>

</style>
