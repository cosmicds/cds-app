import solara
from solara.alias import rv

_STORY_URL = "/hubbles-law/"


@solara.component
def StoryCard(story_name: str, completed_stages: int, total_stages: int):
    progress = int(completed_stages / total_stages * 100) if total_stages > 0 else 0
    display = story_name.replace("_", " ").title()

    with rv.Card(outlined=True, class_="ma-4"):
        with rv.CardText():
            with rv.Row(align="center", class_="mb-2"):
                with rv.Col():
                    solara.Text(display, style="font-size: 1.1rem; font-weight: 500;")
                with rv.Col(cols="auto"):
                    solara.Text(
                        f"{completed_stages} / {total_stages} stages",
                        style="opacity: 0.7;",
                    )
            rv.ProgressLinear(
                value=progress,
                color="primary",
                height=8,
                rounded=True,
                class_="mb-2",
            )
        with rv.CardActions():
            rv.Spacer()
            rv.Btn(
                children=["Open Story"],
                color="primary",
                href=_STORY_URL,
                outlined=True,
            )
