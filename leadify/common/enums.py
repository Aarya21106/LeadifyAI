from enum import Enum

class LeadStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CONVERTED = "converted"
    DEAD = "dead"

class LeadEventType(str, Enum):
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    OUT_OF_OFFICE = "out_of_office"
    SIGNAL_DETECTED = "signal_detected"

class FollowUpDraftStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"
    SKIPPED = "skipped"
    REVISION_NEEDED = "revision_needed"
