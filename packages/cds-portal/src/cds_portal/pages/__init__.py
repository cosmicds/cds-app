from pathlib import Path

import namer
import solara
from cds_client import CDSClient
from cds_client.cookies import sign_student_token
from cds_client.models import StudentCreationInfo
from cds_core.components.location_helper.location_helper import LocationHelper
from solara.alias import rv
from solara_enterprise import auth

from ..layout import Layout
from ..state import get_auth_state, get_portal_state, get_registration_pending

IMG_PATH = Path("static") / "public" / "images"


@solara.component
def Page():
    auth_state = get_auth_state()
    portal_state = get_portal_state()

    authenticated = auth_state.authenticated.value
    loading = portal_state.loading.value

    if authenticated:
        if loading:
            with rv.Container():
                with rv.Row(justify="center", class_="mt-12"):
                    rv.ProgressCircular(indeterminate=True, size=64, color="primary")
        else:
            LocationHelper(url="/overview")
        return

    LandingPage()


@solara.component
def LandingPage():
    solara.Title("CDS Portal")

    current_step = solara.use_reactive(1)
    terms_agreement = solara.use_reactive(False)
    class_code = solara.use_reactive("")
    educator_form_data = solara.use_reactive(
        {
            "first_name": "",
            "last_name": "",
            "email": "",
            "institution": "",
        }
    )
    error = solara.use_reactive("")
    student_auto_username = solara.use_reactive("")
    student_login_username = solara.use_reactive("")
    student_login_class_code = solara.use_reactive("")
    redirect_url = solara.use_reactive("")

    def _generate_student_username():
        name = namer.generate(category="astronomy")
        student_auto_username.set(name)

    solara.use_memo(_generate_student_username, dependencies=None)

    if redirect_url.value:
        LocationHelper(url=redirect_url.value)

    def _on_learner_register(*args):
        if not terms_agreement.value:
            return
        pending = get_registration_pending()
        pending.role = "learner"
        pending.educator_data = None
        redirect_url.set(auth.get_login_url(return_to_path="/"))

    def _on_educator_register(*args):
        error.set("")
        data = educator_form_data.value
        if not data["first_name"].strip() or not data["last_name"].strip():
            error.set("First and last name are required.")
            return
        if not data["email"].strip() or "@" not in data["email"]:
            error.set("A valid email address is required.")
            return
        if not terms_agreement.value:
            error.set("Please agree to the Terms of Service.")
            return
        pending = get_registration_pending()
        pending.role = "educator"
        pending.educator_data = {k: v.strip() for k, v in data.items()}
        redirect_url.set(auth.get_login_url(return_to_path="/"))

    def _on_student_register(*args):
        error.set("")
        code = class_code.value.strip()
        username = student_auto_username.value

        if not code:
            error.set("Please enter a class code.")
            return
        if not terms_agreement.value:
            error.set("Please agree to the Terms of Service.")
            return

        client = CDSClient()
        if not client.classes.validate_code(code):
            error.set("Class code does not exist.")
            return

        try:
            client.students.create(
                StudentCreationInfo(
                    username=username,
                    password=code,
                    classroom_code=code,
                    email=f"{username}@student.cosmicds",
                    institution="",
                    gender="undefined",
                    age=0,
                )
            )
        except Exception as e:
            error.set(f"Could not create account: {e}")
            return

        token = sign_student_token(username)
        redirect_url.set(f"/student-auth?t={token}&next=/")

    def _on_student_login(*args):
        error.set("")
        username = student_login_username.value.strip()
        code = student_login_class_code.value.strip()

        if not username or not code:
            error.set("Please enter your username and class code.")
            return

        client = CDSClient()
        student = client.students.get(username)
        if student is None:
            error.set("Invalid username or class code.")
            return

        classes = client.students.get_classes(username)
        if not any(c.code == code for c in classes):
            error.set("Invalid username or class code.")
            return

        token = sign_student_token(username)
        redirect_url.set(f"/student-auth?t={token}&next=/")

    with rv.Container():
        with rv.Row():
            with rv.Col(cols=6):
                rv.Img(
                    lazy_src=str(IMG_PATH / "hero-side-dark.png"),
                    src=str(IMG_PATH / "hero-side-dark.png"),
                )

            with rv.Col(cols=6):
                with rv.Stepper(
                    v_model=current_step.value,
                    style_="background: transparent",
                    class_="elevation-0",
                ):
                    with rv.StepperItems(style_="min-height: 600px"):
                        # Step 1: role selection
                        with rv.StepperContent(step=1):
                            with rv.Card(
                                outlined=True,
                                hover=True,
                                link=True,
                                class_="mb-4 mr-4 ml-4",
                            ) as learner_card:
                                rv.CardTitle(children=["I am a Learner"])
                                rv.CardSubtitle(
                                    children=[
                                        "Create an account and explore data stories"
                                    ]
                                )
                            solara.v.use_event(
                                learner_card, "click", lambda *_: current_step.set(2)
                            )

                            with rv.Card(
                                outlined=True, hover=True, link=True, class_="ma-4"
                            ) as student_card:
                                rv.CardTitle(children=["I am a Student"])
                                rv.CardSubtitle(
                                    children=["Do stories as part of a directed class"]
                                )
                            solara.v.use_event(
                                student_card, "click", lambda *_: current_step.set(3)
                            )

                            with rv.Card(
                                outlined=True, hover=True, link=True, class_="ma-4"
                            ) as educator_card:
                                rv.CardTitle(children=["I am an Educator"])
                                rv.CardSubtitle(
                                    children=[
                                        "Create and manage classes for directed learning"
                                    ]
                                )
                            solara.v.use_event(
                                educator_card, "click", lambda *_: current_step.set(4)
                            )

                            with rv.Row():
                                with rv.Col(class_="px-4"):
                                    rv.Divider(class_="pb-4")
                                    rv.Text(
                                        children=["Already have a CosmicDS account?"],
                                        class_="pa-4",
                                    )
                                    login_link = rv.Html(
                                        tag="a",
                                        children=["Log in"],
                                        class_="py-4",
                                    )
                                    solara.v.use_event(
                                        login_link,
                                        "click",
                                        lambda *_: current_step.set(5),
                                    )

                        # Step 2: Learner registration
                        with rv.StepperContent(step=2):
                            solara.Button(
                                icon_name="mdi-arrow-left",
                                on_click=lambda *_: current_step.set(1),
                                label="Choose a different role",
                                class_="ma-0",
                            )
                            with rv.Container():
                                with rv.Row():
                                    solara.Markdown("## Sign up as a learner today!")
                                    rv.Text(
                                        children=[
                                            "Learners can experience all data stories with tracked progress and instant feedback."
                                        ]
                                    )
                                with rv.Row():
                                    terms_checkbox = rv.Checkbox(
                                        v_model=terms_agreement.value,
                                        on_v_model=terms_agreement.set,
                                    )
                                    terms_label = solara.Markdown(
                                        "By checking this box, I agree to the Cosmic Data Stories [Terms of Service](https://www.example.com) and [Privacy Policy](https://www.example.com)."
                                    )
                                    rv.Html(
                                        tag="div",
                                        class_="d-flex ma-2",
                                        children=[terms_checkbox, terms_label],
                                    )
                                with rv.Row():
                                    solara.Button(
                                        label="Register with Provider",
                                        classes=["pa-8"],
                                        style="width: 100%;",
                                        disabled=not terms_agreement.value,
                                        on_click=_on_learner_register,
                                    )

                        # Step 3: Student registration
                        with rv.StepperContent(step=3):
                            solara.Button(
                                icon_name="mdi-arrow-left",
                                on_click=lambda *_: current_step.set(1),
                                label="Choose a different role",
                                class_="ma-0",
                            )
                            with rv.Container():
                                with rv.Row():
                                    solara.Markdown("## Sign up as a student today!")
                                with rv.Row():
                                    solara.Text(
                                        "Students are part of a class created by an educator."
                                    )
                                with rv.Row(class_="mt-12 mb-4"):
                                    student_username_field = rv.TextField(
                                        label="Username",
                                        value=student_auto_username.value,
                                        outlined=True,
                                        readonly=True,
                                        hide_details="auto",
                                        append_icon="mdi-refresh",
                                    )
                                    solara.v.use_event(
                                        student_username_field,
                                        "click:append",
                                        lambda *_: _generate_student_username(),
                                    )
                                with rv.Row(class_="mt-0"):
                                    rv.TextField(
                                        label="Class Code",
                                        v_model=class_code.value,
                                        on_v_model=class_code.set,
                                        outlined=True,
                                    )
                                with rv.Row():
                                    terms_checkbox = rv.Checkbox(
                                        v_model=terms_agreement.value,
                                        on_v_model=terms_agreement.set,
                                    )
                                    terms_label = solara.Markdown(
                                        "By checking this box, I agree to the Cosmic Data Stories [Terms of Service](https://www.example.com) and [Privacy Policy](https://www.example.com)."
                                    )
                                    rv.Html(
                                        tag="div",
                                        class_="d-flex ma-2",
                                        children=[terms_checkbox, terms_label],
                                    )
                                if error.value:
                                    solara.Text(error.value, style="color: #ff5252;")
                                with rv.Row():
                                    solara.Button(
                                        label="Register",
                                        disabled=(len(class_code.value) < 5)
                                        or (not terms_agreement.value),
                                        on_click=_on_student_register,
                                        style="width: 100%;",
                                        classes=["pa-8"],
                                    )

                        # Step 4: Educator registration
                        with rv.StepperContent(step=4):
                            solara.Button(
                                icon_name="mdi-arrow-left",
                                on_click=lambda *_: current_step.set(1),
                                label="Choose a different role",
                                class_="ma-0",
                            )
                            with rv.Container():
                                with rv.Row():
                                    solara.Markdown("## Sign up as an educator today!")
                                    rv.Text(
                                        children=[
                                            "Educators can create classes and manage students for guided data story exploration."
                                        ]
                                    )
                                with rv.Row(class_="mt-4"):
                                    rv.Alert(
                                        type="info",
                                        color="yellow",
                                        outlined=True,
                                        children=[
                                            "A verification email will be sent before you can access educator tools."
                                        ],
                                    )
                                with rv.Row():
                                    solara.InputText(
                                        "First name",
                                        value=educator_form_data.value["first_name"],
                                        on_value=lambda v: educator_form_data.set(
                                            {
                                                **educator_form_data.value,
                                                "first_name": v,
                                            }
                                        ),
                                    )
                                with rv.Row():
                                    solara.InputText(
                                        "Last name",
                                        value=educator_form_data.value["last_name"],
                                        on_value=lambda v: educator_form_data.set(
                                            {**educator_form_data.value, "last_name": v}
                                        ),
                                    )
                                with rv.Row():
                                    solara.InputText(
                                        "Email address",
                                        value=educator_form_data.value["email"],
                                        on_value=lambda v: educator_form_data.set(
                                            {**educator_form_data.value, "email": v}
                                        ),
                                    )
                                with rv.Row():
                                    solara.InputText(
                                        "Institution (optional)",
                                        value=educator_form_data.value["institution"],
                                        on_value=lambda v: educator_form_data.set(
                                            {
                                                **educator_form_data.value,
                                                "institution": v,
                                            }
                                        ),
                                    )
                                with rv.Row():
                                    terms_checkbox = rv.Checkbox(
                                        v_model=terms_agreement.value,
                                        on_v_model=terms_agreement.set,
                                    )
                                    terms_label = solara.Markdown(
                                        "By checking this box, I agree to the Cosmic Data Stories [Terms of Service](https://www.example.com) and [Privacy Policy](https://www.example.com)."
                                    )
                                    rv.Html(
                                        tag="div",
                                        class_="d-flex ma-2",
                                        children=[terms_checkbox, terms_label],
                                    )
                                if error.value:
                                    solara.Text(error.value, style="color: #ff5252;")
                                with rv.Row():
                                    solara.Button(
                                        label="Register with Provider",
                                        disabled=not terms_agreement.value,
                                        on_click=_on_educator_register,
                                        style="width: 100%;",
                                        classes=["pa-8"],
                                    )

                        # Step 5: login
                        with rv.StepperContent(step=5):
                            solara.Button(
                                icon_name="mdi-arrow-left",
                                on_click=lambda *_: current_step.set(1),
                                label="Choose a different role",
                                class_="ml-0 mt-0 mr-0",
                            )

                            with rv.Card(flat=True, outlined=True, class_="mt-4"):
                                rv.CardTitle(children=["Learners & Educators"])
                                with rv.CardText():
                                    rv.Btn(
                                        children=["Continue with Provider"],
                                        href=auth.get_login_url(return_to_path="/"),
                                        class_="pa-8",
                                        style_="width: 100%",
                                    )

                            with rv.Card(flat=True, outlined=True, class_="mt-4"):
                                rv.CardTitle(children=["Students"])
                                with rv.CardText():
                                    rv.TextField(
                                        label="Username",
                                        v_model=student_login_username.value,
                                        on_v_model=student_login_username.set,
                                        outlined=True,
                                        hide_details=True,
                                        class_="mb-4"
                                    )
                                    rv.TextField(
                                        label="Class Code",
                                        v_model=student_login_class_code.value,
                                        on_v_model=student_login_class_code.set,
                                        outlined=True,
                                    )
                                    if error.value:
                                        solara.Text(
                                            error.value, style="color: #ff5252;"
                                        )
                                    solara.Button(
                                        label="Log In",
                                        on_click=_on_student_login,
                                        style="width: 100%;",
                                        classes=["pa-8"],
                                    )

                            with rv.Row():
                                with rv.Col():
                                    solara.Markdown(
                                        "By logging in, you agree to the Cosmic Data Stories [Terms of Service](https://www.example.com) and [Privacy Policy](https://www.example.com)."
                                    )

    with rv.Container():
        with rv.Row(justify="space-around"):
            with rv.Col(cols=12, md=4):
                solara.Markdown("#Absolutely the best learning method for my students.")
                solara.Markdown("####- Albert Einstein")
            with rv.Col(cols=12, md=4):
                solara.Markdown(
                    "#I feel like the guided stories really help me to understand the science!"
                )
                solara.Markdown("####- Socrates")
            with rv.Col(cols=12, md=4):
                solara.Markdown("#Perfect platform for exploring scientific concepts.")
                solara.Markdown("####- Marie Curie")
