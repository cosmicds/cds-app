# cds-client

Typed Python client for the CosmicDS backend API.

## Installation

```bash
pip install cds-client
```

Set your API key in the environment before use:

```bash
export CDS_API_KEY="your-api-key"
```

## Quick start

```python
from cds_client import CDSClient

client = CDSClient()
```

All endpoints are accessible as attributes on the client. The `hubble` attribute
provides a sub-client for Hubble's Law story endpoints.

---

## Students

```python
# Fetch by username (hashed string) or numeric ID
student = client.students.get("abc123hash")
student = client.students.get(42)

# All students
students = client.students.get_all()

# Create a student account
from cds_client import StudentCreationInfo

client.students.create(StudentCreationInfo(
    username="stargazer-7",
    password="class-code",
    classroom_code="CLASS01",
))

# Classes a student is enrolled in
classes = client.students.get_classes("abc123hash")

# Remove from a class
client.students.remove_from_class("abc123hash", class_id=5)

# Mark a student as ignored for a story
client.students.ignore_for_story("abc123hash", "hubbles_law", ignore=True)
```

---

## Educators

```python
# Fetch by username or numeric ID — returns None if not found
educator = client.educators.get("abc123hash")

# All educators
educators = client.educators.get_all()

# Create an educator account
from cds_client import EducatorCreationInfo

client.educators.create(EducatorCreationInfo(
    username="abc123hash",
    password="",
    first_name="Jane",
    last_name="Smith",
    email="jane@example.edu",
    institution="State University",
))

# Classes managed by an educator
classes = client.educators.get_classes(educator.id)
```

---

## Classes

```python
# Fetch a class by code or numeric ID — returns None if not found
classroom = client.classes.get("CLASS01")
classroom = client.classes.get(5)

# Create a class
from cds_client import ClassCreationInfo

classroom = client.classes.create(ClassCreationInfo(
    educator_id=educator.id,
    name="Intro Astronomy Fall 2026",
    expected_size=30,
    story_name="hubbles_law",
))

# Enrollment
students = client.classes.get_roster(class_id=5)
size = client.classes.get_size(class_id=5)
expected = client.classes.get_expected_size(class_id=5)

# Add a student to a class
client.classes.join(username="stargazer-7", class_code="CLASS01")

# Validate a code before using it
if client.classes.validate_code("CLASS01"):
    print("Code is valid")

# Active status for a story
active = client.classes.get_active(class_id=5, story_name="hubbles_law")
client.classes.set_active(class_id=5, story_name="hubbles_law", active=True)

# Delete a class
client.classes.delete("CLASS01")
```

---

## Stories & stage state

```python
# Story-level state
state = client.stories.get_story_state(student_id=42, story_name="hubbles_law")

client.stories.put_story_state(
    student_id=42,
    story_name="hubbles_law",
    state={"current_stage": "intro", "completed": False},
)

client.stories.patch_story_state(
    student_id=42,
    story_name="hubbles_law",
    patch={"completed": True},
)

# Stages
stages = client.stories.get_stages("hubbles_law")
completed = client.stories.count_completed_stages("hubbles_law", student_id=42)

# Stage-level state
stage_state = client.stories.get_stage_state(
    student_id=42, story_name="hubbles_law", stage_name="intro"
)

client.stories.put_stage_state(
    student_id=42,
    story_name="hubbles_law",
    stage_name="intro",
    state={"seen": True},
)

client.stories.delete_stage_state(
    student_id=42, story_name="hubbles_law", stage_name="intro"
)

# Questions
question = client.stories.get_question(tag="distance-ladder-q1")
questions = client.stories.get_questions("hubbles_law")
```

---

## Hubble's Law

The `client.hubble` sub-client groups the Hubble's Law story endpoints.

### Galaxies

```python
# Full catalog
galaxies = client.hubble.galaxies.get_all()

# Filtered by type
spirals = client.hubble.galaxies.get_all(types=["Sp"])

# Sample (example) galaxy
sample = client.hubble.galaxies.get_sample()

# Download a spectrum (requires astropy)
spectrum = client.hubble.galaxies.get_spectrum(
    galaxy_type="spiral",
    name="spect-0001",
)
print(spectrum.wave, spectrum.flux)

# Flag bad data
client.hubble.galaxies.mark_bad(galaxy_id=7)
client.hubble.galaxies.mark_spectrum_bad(galaxy_name="spect-0001")
```

### Measurements

```python
# Student measurements
measurements = client.hubble.measurements.get(student_id=42)
one = client.hubble.measurements.get_one(student_id=42, galaxy_id=7)

# Submit or update a measurement
from cds_client import HubbleMeasurementInput

client.hubble.measurements.submit(HubbleMeasurementInput(
    student_id=42,
    galaxy_id=7,
    velocity=1500,
    distance=22.3,
))

client.hubble.measurements.delete(student_id=42, galaxy_identifier=7)

# Class-wide measurements
class_data = client.hubble.measurements.get_class(
    student_id=42,
    class_id=5,
    complete_only=True,
)

# Aggregate all-data snapshot
all_data = client.hubble.measurements.get_all_data(class_id=5)
```

---

## Error handling

All API errors raise subclasses of `CDSAPIError`:

```python
from cds_client import CDSAPIError, CDSNotFoundError, CDSAuthError, CDSConflictError

try:
    student = client.students.get("nonexistent")
except CDSNotFoundError:
    print("Student not found")
except CDSAuthError:
    print("Invalid or missing API key")
except CDSConflictError:
    print("Resource already exists")
except CDSAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

Convenience methods (e.g. `students.get`, `educators.get`, `classes.get`) already
catch `CDSNotFoundError` internally and return `None`, so you only need explicit
error handling when calling create/delete operations or other methods that raise on
failure.
