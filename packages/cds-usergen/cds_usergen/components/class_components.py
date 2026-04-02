
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

from .validated_inputs import ValidatedTextInput, ValidatedInputInt
from .components import *
from ..validation import validate_username, username_error_message, numDigits

@solara.component
def GenerateForClassButton(
    connection_id: solara.Reactive,
    job: solara.Reactive,
    username_error: solara.Reactive[str],
    start_index: solara.Reactive[int],
    end_index: solara.Reactive[int],
    prefix: solara.Reactive[str],
    howMany: solara.Reactive[int],
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
        suffix_width = numDigits(howMany.value)
        usernames = [getUsername(prefix.value, suffix_width, i) for i in range(start_index.value, end_index.value + 1)]
        password_value = None if use_username_as_password.value else (password.value or None)
        passwords = None if use_username_as_password.value else [password_value] * len(usernames)
        users = auth0.create_user_file_from_list(
            usernames=usernames,
            prefix=prefix.value,
            passwords=passwords,
            domain=email_domain.value,
            create_file=False,
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
        print(f"username:{prefix.value}*")
        return auth0.search_users(domain=auth0.DOMAIN, access_token=auth0.BEAERER_TOKEN, query=f"username:{prefix.value}*")

    def check_and_maybe_create():
        users = search_users_action()
        suffix_width = numDigits(howMany.value)
        target_usernames = {getUsername(prefix.value, suffix_width, i) for i in range(start_index.value, end_index.value + 1)}
        if users is None:
            can_submit.value = False
            return
        has_conflict = any(user.get("username", "") in target_usernames for user in users)
        if has_conflict:
            can_submit.value = False
            return
        can_submit.value = True
        create_users_action()

    if not can_submit.value:
        solara.Error("That username is already use")
    solara.Button(
        label="Generate Users",
        disabled=(
            username_error.value != ""
            or start_index.value is None
            or end_index.value is None
            or prefix.value == ""
            or ((not use_username_as_password.value) and ((password.value is None) or len(password.value) < 5 or " " in password.value))
        ),
        on_click=check_and_maybe_create,
    )


            

@solara.component
def CreateStudentsForClass(
    class_code_value="",
    howManyValue=0,
    padding=0,
):
    solara.Title("Create Usernames")
    # --- Per-session reactive state (use_reactive) ---
    connection_id = solara.use_reactive(None)
    job = solara.use_reactive(None)
    username_error = solara.use_reactive("")
    prefix = solara.use_reactive("")
    class_code = solara.use_reactive(class_code_value)
    @computed
    def email_domain():
        return f"{class_code.value}.class"
    password = solara.use_reactive(None)
    use_username_as_password = solara.use_reactive(True)

    # we need to find out if this class already has some students
    class_user_count = solara.use_reactive(0)
    create_more = solara.use_reactive(False)
    start_index = solara.use_reactive(1)
    howManyValueRef = solara.use_reactive(howManyValue)
    @computed
    def howMany():
        return howManyValueRef.value + padding
    end_index = solara.use_reactive(howMany.value if howMany.value > 0 else 1)

    # Load connection on mount
    ready = solara.use_reactive(False)
    MakeConnection(ready, connection_id, quiet=True)



    async def search_class_users():
        if connection_id.value is None:
            return []
        return auth0.search_users(
            domain=auth0.DOMAIN,
            access_token=auth0.BEAERER_TOKEN,
            query=f"email:*@{email_domain.value}",
        )

    class_users_task = use_task(search_class_users, dependencies=[connection_id.value, class_code.value])
    
    def parse_pattern(user):
        if user.get('family_name', None):
            return user.get('family_name')
        pattern = re.compile(r'(.*?)(\d+)$')
        match = pattern.match(user.get('username', ''))
        if match and len(match.groups())>1:
            return match.groups()[0]
        return None
        
        

    def get_users_for_class():
        matched = class_users_task.value if class_users_task.finished and class_users_task.value is not None else []
        class_user_count.value = len(matched)
        if len(matched) == 0:
            start_index.set(1)
            return
        # just incase there is more than 1
        unique_patterns = []
        for user in matched:
            name = parse_pattern(user)
            if name is not None and name not in unique_patterns:
                unique_patterns.append(name)
        prefix.set(unique_patterns[0])
        print(unique_patterns)
        count = len([u for u in matched if u.get('family_name') == unique_patterns[0] ])
        start_index.set(count + 1)

    solara.use_effect(get_users_for_class, [class_users_task.value])

    def sync_end_index():
        end_index.set(start_index.value + howMany.value - 1)

    solara.use_effect(sync_end_index, [howMany.value, start_index.value])

    def reset_state():
        job.set(None)
        username_error.set("")
        prefix.set("")
        password.set(None)
        use_username_as_password.set(True)
        class_user_count.value = 0
        start_index.set(1)
        sync_end_index()

    solara.use_effect(reset_state, [class_code.value, howMany.value])

    if not class_users_task.finished:
        solara.ProgressLinear(True, color='red')
        return
    
    with solara.Column():
        with solara.Row(classes=["mx-4"]):
            with solara.Column():
                if class_user_count.value > 0:
                    solara.Info(f"There are {class_user_count.value} usernames already assigned to this class. You may not create more")
                    return
                
                if padding > 0:
                    solara.Text(f"Creating {howMany.value - padding} (+{padding} extra) usernames for class code: {class_code.value}")
                else:
                    solara.Text(f"Creating {howMany.value} usernames for class code: {class_code.value}")
                with solara.Row():
                    SetUsernamePrefix(prefix, howMany)
                        
                    # PasswordInput(password, use_username_as_password) # for password to be the username
                ValidationEffect(howMany, prefix, username_error)
                GenerateForClassButton(connection_id, job, username_error, start_index, end_index, prefix, howMany, email_domain, password, use_username_as_password)
                JobStatusPanel(job, connection_id)
