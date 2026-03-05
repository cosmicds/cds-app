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

from ..components import *
from ..validation import validate_username, username_error_message, numDigits



DEFAULT_EMAIL_DOMAIN = "test.edu"  # email will look like imfake_01@email_domain


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
    username_error = solara.use_reactive("")
    howMany = solara.use_reactive(2)
    prefix = solara.use_reactive("testuser")
    email_domain = solara.use_reactive(DEFAULT_EMAIL_DOMAIN)
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
    
    rv.Html(tag="hr")
    
    with solara.Row():
        solara.Text("Simplified class view")
        CreateStudentsForClass("frodo", howMany.value)
