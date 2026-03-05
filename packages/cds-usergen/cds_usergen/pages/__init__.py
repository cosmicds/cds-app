import solara
from solara.alias import rv
from solara.lab import use_task, Task, computed

from ..auth0_interfaces import auth0, MakeConnection
from math import log10, floor
import json
import asyncio
from io import StringIO
import re
from typing import Optional

from ..components import ValidatedTextInput, ValidatedInputInt
from ..validation import validate_username, username_error_message, numDigits

"""
 TODO: Get Class info
  - display class info for the teachers
  - we need the class code (this will be the email domain)
  - we need to check if the class already has users assigned to it an how many
  - our auth0 call does not allow name-collision
"""

EMAIL_DOMAIN = "test.edu"  # email will look like imfake_01@email_domain



@solara.component
def JobStatusDisplay(job_status):
    if job_status is None:
        return solara.Info("No job started yet.")
    print('job_status in display', job_status)
    summary = job_status.get('summary', {})
    failed = summary.get('failed', 0)
    inserted = summary.get('inserted', 0)
    updated = summary.get('updated', 0)
    total = summary.get('total', 0)
    if failed == 0:
        return solara.Success(f"Import completed! {job_status}")
    else:
        with solara.Div() as main:
            solara.Error(f"Import failed for {failed} users out of {total}.")
            job_errors = auth0.get_job_errors(
                job_status,
                domain=auth0.DOMAIN,
                access_token=auth0.BEAERER_TOKEN,
            )
            print('job_errors', job_errors)
            for error in job_errors:
                email = error['user']['email']
                username = error['user']['username']
                error_codes = [e['code'] for e in error['errors']]
                error_messages = [e['message'] for e in error['errors']]
                solara.Error(f"User {username} ({email}) failed with errors: {error_codes} - {error_messages}")
        return main


@solara.component
def UsernameInputs(howMany: solara.Reactive[int], prefix: solara.Reactive[str], email_domain: solara.Reactive[str]):
    """
    Username input fields.
    
    This the username input has validation
    
    Use a standalone component to keep renders only in the child component
    """
    
    with solara.Row():
        with solara.Columns(widths = [1, 2]):
            solara.Text("How many usernames would you like to create: ")
            ValidatedInputInt(
                max = 5,
                label='How many?',
                value=howMany,
                clearable=True,
            )
        
    with solara.Row():
        with solara.Columns(widths=[1,2]):
            solara.Text("What username would you like for your students. A number will be appended to the end")
            with solara.Column():
                ValidatedTextInput(
                    label='Username Base',
                    value=prefix,
                    validator=lambda v: validate_username(v, howMany.value),
                    error_message=lambda v: username_error_message(v, howMany.value),
                )
                solara.Text(f"Username preview: {prefix.value}01")

    with solara.Row():
        with solara.Columns(widths=[1, 2]):
            solara.Text("Email domain for the generated accounts:")
            with solara.Row():
                solara.InputText(
                    label='Email Domain',
                    value=email_domain,
                    continuous_update=True,
                )
                solara.Button(
                    icon_name="mdi-refresh",
                    icon=True,
                    on_click=lambda: email_domain.set(EMAIL_DOMAIN),
                )


@solara.component
def PasswordInput(password: solara.Reactive[Optional[str]], use_username_as_password: solara.Reactive[bool]):
    password_input = solara.use_reactive(password.value or "")

    @computed
    def password_error():
        if use_username_as_password.value:
            return None
        if len(password_input.value) == 0:
            return "Password required when not using username as password."
        if len(password_input.value) < 5:
            return "Password must be 5 or more characters long."
        if " " in password_input.value:
            return "Password cannot contain spaces."
        return None

    def sync_password_mode():
        if use_username_as_password.value:
            password.set(None)
            password_input.set("")

    def sync_password_value():
        password.set(password_input.value or None)

    solara.use_effect(sync_password_mode, [use_username_as_password.value])
    solara.use_effect(sync_password_value, [password_input.value])

    with solara.Row():
        with solara.Columns(widths=[1, 2]):
            solara.Checkbox(
                label="Use username as password",
                value=use_username_as_password,
            )

            if not use_username_as_password.value:
                with solara.Column():
                    solara.Text("Set a common password for all users (not recommended).")
                    solara.InputText(
                        label="Set common password for all users",
                        value=password_input,
                        continuous_update=True,
                    )
                    if password_error.value:
                        solara.Error(password_error.value)


@solara.component
def GenerateButton(
    connection_id: solara.Reactive,
    job: solara.Reactive,
    username_error: solara.Reactive[str],
    howMany: solara.Reactive[int],
    prefix: solara.Reactive[str],
    email_domain: solara.Reactive[str] = None,
    password: solara.Reactive[Optional[str]] = None,
    use_username_as_password: solara.Reactive[bool] = None,
):
    """
    Submit the request to create the usernames to auth0
    TODO: this currently does not perform any additional
        validation, or check the user isn't spamming us
    
    Creates a file-like StringIO to pass to the 
    
    Reads username_error, howMany, prefix .value — only this re-renders
    
    The job should be passed back into the JobStatusPanel or something else 
    to keep track of the jobs completeion using auth0.check_job_status
    """
    
    can_submit = solara.use_reactive(True)
    def create_users_action():
        if not can_submit.value: 
            return
            
        if connection_id.value is None:
            raise ValueError("Connection ID is not loaded yet.")
        password_value = None if use_username_as_password.value else (password.value or None) # '' or None => None
        users = auth0.create_user_file(
            prefix.value,
            domain=email_domain.value,
            N=howMany.value,
            password=password_value,
            create_file=False
        )
        user_json_string = json.dumps(users, indent=4)
        file_like_object = StringIO(user_json_string)
        job.value = auth0.start_import_job(
            filename=file_like_object,
            connection_id=connection_id.value,
            domain=auth0.DOMAIN,
            access_token=auth0.BEAERER_TOKEN,
        )
    
    # TODO: Better checks and logic
    def search_users_action():
        print(f'username:{prefix.value}* AND email:{prefix.value}*@{email_domain.value}')
        return auth0.search_users(
            domain=auth0.DOMAIN,
            access_token=auth0.BEAERER_TOKEN,
            query=f'username:{prefix.value}* AND email:{prefix.value}*@{email_domain.value}'
        )
    
    def check_and_maybe_create():
        users = search_users_action()
        if len(users) > 0:
            can_submit.value = False
            return
        create_users_action()
    
    if not can_submit.value:
        solara.Error("That username is already use [TODO: Implement better checkes]")
    solara.Button(
        label="Generate Users",
        disabled=(
            username_error.value != ''
            or howMany.value <= 0
            or prefix.value == ''
            or (
                (not use_username_as_password.value) 
                and (
                    (password.value is None) 
                    or len(password.value) < 5 
                    or " " in password.value
                    )
                )
        ),
        on_click=check_and_maybe_create,
    )

@solara.component
def SearchButton(
    connection_id: solara.Reactive,
    prefix: solara.Reactive[str],
    email_domain: solara.Reactive[str] = None,
):
    """
    Just a wrapper to search for a particular username in the username list
    
    The idea being that we can look up if the username exists
    
    
    """
    users = solara.use_reactive([])
    num_matches = solara.use_reactive(0)

    def search_users_action():
        initialUserList = auth0.search_users(
            domain=auth0.DOMAIN,
            access_token=auth0.BEAERER_TOKEN,
            # username:*<prefix>* AND email:*@<EMAIL_DOMAIN>*
            query=f'username:{prefix.value}* AND email:{prefix.value}*@{email_domain.value}'
        )
        # begins with prefix followd by at least one digit (at the end)
        pattern = re.compile(rf"^{prefix.value}\d+$")
        users.value = [u for u in initialUserList if pattern.match(u.get('username', ''))]
        

    solara.Button(
        label="Search for Username prefix",
        disabled=prefix.value == '',
        on_click=search_users_action,
    )
    
    if users.value is not None and len(users.value) > 0:
        solara.Text(f"Searched for username:{prefix.value}\d+ AND email:{prefix.value}*@{email_domain.value}")
        solara.Markdown(f"<pre>{json.dumps(users.value, indent=4)}</pre>")
    

@solara.component
def JobStatusPanel(job: solara.Reactive, connection_id: solara.Reactive):
    """Isolated component for job status display.
    
    Only re-renders when job.value changes (i.e. when a job is started).
    """
    

    async def load_job_status():
        return auth0.check_job_status(
            job.value,
            connection_id=connection_id.value,
            domain=auth0.DOMAIN,
            access_token=auth0.BEAERER_TOKEN,
            sleep=5,
        )

    job_status_task = use_task(load_job_status, dependencies=[job.value])
    
    if job.value is None:
        return

    if not job_status_task.finished:
        solara.Info("Starting import job...")
    else:
        status = job_status_task.value
        JobStatusDisplay(status)


@solara.component
def ValidationEffect(howMany: solara.Reactive[int], prefix: solara.Reactive[str], username_error: solara.Reactive[str]):
    """Isolated component that runs the validation side-effect.
    
    Reads howMany.value and prefix.value to validate, and writes
    to username_error — but this re-render is cheap (no UI output).
    """
    def validate_prefix():
        totalDigits = numDigits(howMany.value) + len(prefix.value)
        if totalDigits > auth0.MAX_USERNAME_LENGTH:
            username_error.value = 'Username must be less than 15 characters. It is currently {}'.format(totalDigits)
            return
        username_error.value = ''
    
    solara.use_effect(validate_prefix, [howMany.value, prefix.value])
    
    if len(username_error.value) > 0:
        solara.Error(label=username_error.value, dense=True,text=True,outlined=False)
        


@solara.component
def JSONPreview(
    prefix: solara.Reactive[str],
    howMany: solara.Reactive[int],
    email_domain: solara.Reactive[str] = None,
    password: solara.Reactive[Optional[str]] = None,
    use_username_as_password: solara.Reactive[bool] = None,
):
    trigger = solara.use_reactive(0)

    async def generate_preview():
        if trigger.value == 0:
            return None
        password_payload = None if use_username_as_password.value else (password.value or None)
        prev = auth0.create_user_file(prefix.value, domain=email_domain.value, N=howMany.value, password=password_payload, create_file=False)
        [user.pop('password_hash') for user in prev]
        if password_payload is None:
            [user.update({'password': user['username']}) for user in prev]
        else:
            [user.update({'password': password_payload}) for user in prev]
        return json.dumps(prev, indent=4)

    task = use_task(generate_preview, dependencies=[trigger.value])

    solara.Markdown("### Preview JSON")
    solara.Markdown("For Development purposes only")
    solara.Button(
        label="Generate Preview JSON",
        on_click=lambda: trigger.set(trigger.value + 1),
    )
    if task.finished and task.value is not None:
        with solara.Div(style="height: 400px; overflow-y: auto;"):
            solara.Markdown(f"<pre id='preview-json'>{task.value}</pre>")
    
    elif task.pending and trigger.value > 0:
        solara.Info("Generating preview...")

@solara.component
def Page():
    """Top-level page component.
    
    Note about how Solara works. The component that reads .value get's rerendered
    so we want to rely heavily on child components and passing reactives.
    """
    solara.Title("Create Usernames")
    # --- Per-session reactive state (use_reactive) ---
    connection_id = solara.use_reactive(None)
    job = solara.use_reactive(None)
    username_error = solara.use_reactive('')
    howMany = solara.use_reactive(2)
    prefix = solara.use_reactive('testuser')
    email_domain = solara.use_reactive(EMAIL_DOMAIN)
    password = solara.use_reactive(None)
    use_username_as_password = solara.use_reactive(True)

    # Load connection on mount
    ready = solara.use_reactive(False)
    MakeConnection(ready, connection_id)
    

    with solara.Column():
        with solara.Row(classes=["mx-4"]):
            with solara.Column():
                
                UsernameInputs(howMany, prefix, email_domain)
                PasswordInput(password, use_username_as_password)
                ValidationEffect(howMany, prefix, username_error)
                GenerateButton(connection_id, job, username_error, howMany, prefix, email_domain, password, use_username_as_password)
                SearchButton(connection_id, prefix, email_domain)
                JobStatusPanel(job, connection_id)
    with solara.Column():
        JSONPreview(prefix, howMany, email_domain, password, use_username_as_password)
