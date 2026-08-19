#    Copyright 2026 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""What a reviewer works through, and what is raised for them to look at."""

import logging
from collections.abc import Iterable, Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseImage,
    DatabaseItem,
    NotAllowedActionError,
)
from slidetap.model import (
    AnyItem,
    BatchStatus,
    MetadataImportCompleteness,
    MetadataSearchResult,
    NonValidItem,
    ReviewIssue,
    ReviewIssueSource,
    ReviewQueueItem,
    ReviewStatus,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class ReviewService:
    """Reviewing: what is flagged, why, and what a reviewer is shown of it.

    A review unit answers for the items under it, so most of this is asked of
    a unit and answered by looking at what it holds.
    """

    def __init__(
        self,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ) -> None:
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def set_review_status(
        self,
        item_uid: UUID,
        status: ReviewStatus,
        reason: str | None = None,
        session: Session | None = None,
    ) -> AnyItem | None:
        """Move an item to a review status.

        Parameters
        ----------
        item_uid: UUID
            The item to move.
        status: ReviewStatus
            The status to move to. ``REVIEWED`` is refused for a review unit
            that holds something invalid, which is flagged instead, and
            ``FLAGGED`` is refused outright — see below. Every other move is
            made as asked.
        reason: str | None
            Unused, and kept so that a client that still sends one is not
            refused for it.
        session: Session | None
            Session to move the item in.

        Returns
        -------
        AnyItem | None
            The item as it now stands, or None where there is no such item.

        Raises
        ------
        NotAllowedActionError
            The unit holds something invalid and cannot be signed off, or
            review was asked for through here rather than by raising an issue.
        """
        if status == ReviewStatus.FLAGGED:
            # Asking for review is raising an issue, so that what was asked for
            # is on record beside everything else raised on the unit, and can
            # be settled one at a time. A flag written straight onto the item
            # says only that somebody wanted something, and nothing about what
            # would settle it — which is what left cases sitting in the queue
            # after the thing that flagged them had been dealt with.
            raise NotAllowedActionError(
                "Review is asked for by raising an issue on the item it is "
                "about, not by flagging the unit."
            )
        refusal = None
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            if status == ReviewStatus.REVIEWED:
                refusal = self._invalid_descendants_reason(item, session)
            if refusal is not None:
                item.review_status = ReviewStatus.FLAGGED
                item.review_reason = refusal
            else:
                item.review_status = status
            model = item.model
        # Raised outside the session, which rolls back what it holds when an
        # exception leaves it: the flag is the point of refusing, and would go
        # with it.
        if refusal is not None:
            raise NotAllowedActionError(refusal)
        return model

    def flag_for_review(
        self,
        item_uid: UUID,
        reason: str,
        session: Session | None = None,
    ) -> AnyItem | None:
        """Ask for an item to be reviewed, leaving one already flagged alone.

        A second reason would overwrite the first, and the first is the one that
        was there when nobody had looked yet.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            if item.review_status == ReviewStatus.FLAGGED:
                return item.model
            item.review_status = ReviewStatus.FLAGGED
            item.review_reason = reason
            return item.model

    def review_unit_of(self, item: DatabaseItem) -> DatabaseItem | None:
        """The item that would be reviewed if ``item`` needed a second look.

        The nearest thing above it whose schema declares itself a unit for
        review, or the item itself where its own schema does. Nothing, for an
        item that sits under no such unit.
        """
        unit = self._schema_service.review_unit
        if unit is None or not self._schema_service.review_unit_covers(item.schema_uid):
            return None
        if item.schema_uid == unit.schema_uid:
            return item
        return self._database_service.get_ancestor(item, {unit.schema_uid})

    def review_unit_uids_in(
        self, result: MetadataSearchResult, uid_remap: Mapping[UUID, UUID]
    ) -> Iterable[UUID]:
        """The review units the result produced, by their uid in the database.

        Taken from the items rather than from the result's entry-level item:
        an importer names that one for its own reasons, and it need be neither
        a review unit nor the only one the result holds.
        """
        if self._schema_service.review_unit is None:
            return ()
        return (
            uid_remap.get(item.uid, item.uid)
            for item in result.items
            if item.schema_uid == self._schema_service.review_unit.schema_uid
        )

    def check_imported_review_unit(self, item_uid: UUID, session: Session) -> None:
        """Bring what is raised on a review unit up to date with what was just
        imported into it: raised for what is not valid, settled for what is.

        Both halves, because an import runs again. The second run brings in
        what was missing the first time, and nothing else would notice that
        what was raised for it has been dealt with — leaving the case in the
        queue for something that is no longer wrong with it.

        On its own savepoint: a review unit that imported cleanly is worth
        keeping whether or not it could be flagged, and an exception left to
        reach the enclosing transaction would take its items down with it. One
        that repeated would leave the unit permanently unimportable.
        """
        try:
            with session.begin_nested():
                self.flag_review_unit_if_invalid(item_uid, session=session)
                self.settle_what_is_valid_under(item_uid, session=session)
        except Exception:
            self._logger.error(
                f"Failed to check imported review unit {item_uid}", exc_info=True
            )

    def settle_what_is_valid_under(
        self,
        unit_uid: UUID,
        session: Session | None = None,
    ) -> int:
        """Settle what validation raised under a unit on the items that are
        valid again, and take the unit out of the queue if that was the last of
        it.

        Only what validation raised: what a person or an import asked to have
        looked at is settled by somebody looking at it, whatever the items say.

        Returns
        -------
        int
            How many were settled.
        """
        with self._database_service.get_session(session) as session:
            unit = self._database_service.get_optional_item(session, unit_uid)
            if unit is None:
                return 0
            settled = 0
            for issue in list(
                self._database_service.get_review_issues(session, unit.uid)
            ):
                if issue.source != ReviewIssueSource.VALIDATION:
                    continue
                if not self._validation_service.item_is_valid_for_now(
                    issue.item, session
                ):
                    continue
                self.item_became_valid(
                    issue.item_uid, review_unit=unit, session=session
                )
                settled += 1
            return settled

    def get_review_queue(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        review_status: ReviewStatus | None = None,
    ) -> list[ReviewQueueItem]:
        """The items of a schema a reviewer works through, and where they stand.

        Without a status this is every item of the schema: a reviewer may want
        to look at something nothing flagged, and needs it in the same list to
        get to it.

        Sorted by identifier so the queue is worked through in a stable order
        rather than in whatever order the database returns.
        """
        with self._database_service.get_session() as session:
            items = self._database_service.get_items(
                session,
                self._schema_service.items[item_schema_uid],
                dataset_uid,
                batch_uid,
                review_status=review_status,
            )
            items = list(items)
            open_issues = self._database_service.count_open_issues(
                session, (item.uid for item in items)
            )
            return sorted(
                (
                    ReviewQueueItem(
                        uid=item.uid,
                        identifier=item.identifier,
                        pseudonym=item.pseudonym,
                        review_status=item.review_status,
                        review_reason=item.review_reason,
                        last_saved=item.last_saved,
                        open_issues=open_issues.get(item.uid, 0),
                    )
                    for item in items
                ),
                key=lambda item: item.identifier,
            )

    def flag_invalid_review_units(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        session: Session | None = None,
    ) -> int:
        """Ask for review of every review unit holding something invalid, and
        return how many were flagged.

        Asked for rather than done on import: an application decides for itself
        when its items are supposed to be valid. One that imports metadata
        first and images after has slides without images for as long as that
        takes, and flagging every case at the end of the metadata import says
        only that the import is not finished yet. Run this once the pieces are
        expected to be in place, and what it finds is what is actually wrong.

        What is found is raised as an issue on the item it is about, one open
        at a time per item, so running it twice adds nothing the first run did
        not and settling one item does not settle the rest.
        """
        review_unit = self._schema_service.review_unit
        if review_unit is None:
            return 0
        flagged = 0
        with self._database_service.get_session(session) as session:
            units = self._database_service.get_items(
                session,
                self._schema_service.items[review_unit.schema_uid],
                dataset_uid,
                batch_uid,
            )
            for unit in units:
                if self._raise_on_invalid_under(unit, session):
                    flagged += 1
        return flagged

    def _raise_on_invalid_under(self, unit: DatabaseItem, session: Session) -> bool:
        """Raise an issue on everything under ``unit`` that is not as valid as
        it is expected to be, and answer whether anything was.

        The unit is given as the one to answer on rather than worked out again
        per item: it is the unit being swept, and walking back up from every
        item to arrive at the same answer is work for nothing.
        """
        invalid_items, _ = self._issues_under(unit, session)
        for invalid_item in invalid_items:
            self.item_became_invalid(
                invalid_item.uid, review_unit=unit, session=session
            )
        return bool(invalid_items)

    def flag_review_unit_if_invalid(
        self,
        item_uid: UUID,
        session: Session | None = None,
    ) -> bool:
        """Flag one review unit that holds something invalid.

        Parameters
        ----------
        item_uid: UUID
            The review unit to look under. An item that is not one holds
            nothing to answer for and is left alone.
        session: Session | None
            Session to look and to flag in.

        Returns
        -------
        bool
            Whether it holds something invalid. A unit already flagged keeps
            the reason it was flagged with, since an importer that found
            something specific said more than a count of invalid items does.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return False
            return self._raise_on_invalid_under(item, session)

    def raise_issue(
        self,
        item_uid: UUID,
        reason: str,
        source: ReviewIssueSource,
        session: Session | None = None,
    ) -> ReviewIssue | None:
        """Record something raised as wrong with an item, and flag the review
        unit it is under so that somebody answers for it.

        Raised on the item and answered on the unit: a block that looks wrong
        is usually only decidable with the whole case in front of you, so what
        is flagged is the case while what the issue is about stays the block.

        Parameters
        ----------
        item_uid: UUID
            The item the issue is about. It may be the review unit itself.
        reason: str
            What is wrong with it, as whatever raised it puts it.
        source: ReviewIssueSource
            What kind of thing raised it. Which one is not recorded.
        session: Session | None
            Session to record it in.

        Returns
        -------
        ReviewIssue | None
            None where there is no such item, and where it sits under no review
            unit — there would be nobody to answer for it.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            unit = self.review_unit_of(item)
            if unit is None:
                return None
            return self._raise_issue_on(session, item, unit, reason, source)

    def _raise_issue_on(
        self,
        session: Session,
        item: DatabaseItem,
        unit: DatabaseItem,
        reason: str,
        source: ReviewIssueSource,
    ) -> ReviewIssue:
        """Record an issue on ``item``, answered on ``unit``.

        Split out for the caller that read the unit before the change it is
        reporting: an edit can be the removal of the last link upward, and
        after it there is no way left to tell what the item was part of.
        """
        issue = self._database_service.add_review_issue(
            session, item, unit, reason, source
        )
        self.flag_for_review(unit.uid, f"{item.identifier}: {reason}", session=session)
        session.flush()
        return issue.model

    def item_validity_changed(
        self,
        item_uid: UUID,
        was_valid: bool,
        is_valid: bool,
        review_unit: DatabaseItem | None = None,
        session: Session | None = None,
    ) -> None:
        """Report an item crossing between valid and not, as its validity is
        expected to stand at this point in the batch's life.

        Reported as a crossing rather than as a state, since validation runs
        over and over on items nothing has happened to: a remap validates an
        item once per attribute, and an item that was already invalid before
        the change has nothing new to say about it.

        Parameters
        ----------
        item_uid: UUID
            The item that changed.
        was_valid: bool
            What ``ValidationService.item_is_valid_for_now`` said before the
            change.
        is_valid: bool
            What it says after it.
        review_unit: DatabaseItem | None
            The unit the item was under, where the caller read it before a
            change that could have detached it. Worked out from the item when
            not given.
        session: Session | None
            Session to record it in.
        """
        if was_valid == is_valid:
            return
        if is_valid:
            self.item_became_valid(item_uid, review_unit=review_unit, session=session)
        else:
            self.item_became_invalid(item_uid, review_unit=review_unit, session=session)

    def item_became_invalid(
        self,
        item_uid: UUID,
        review_unit: DatabaseItem | None = None,
        session: Session | None = None,
    ) -> ReviewIssue | None:
        """Record that an item is no longer as valid as it is expected to be.

        One open issue per item: an item that goes invalid, is worked on, and
        goes invalid again before anybody looked has one thing wrong with it
        rather than two. What is wrong is read off the item rather than said by
        whoever noticed, so that every path that finds it words it the same.

        Returns
        -------
        ReviewIssue | None
            The issue raised, or None where there is no such item, where it
            sits under no review unit, or where one is already open on it.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            already_open = next(
                iter(
                    self._database_service.get_open_issues_for_item(
                        session, item.uid, ReviewIssueSource.VALIDATION
                    )
                ),
                None,
            )
            if already_open is not None:
                return already_open.model
            unit = review_unit if review_unit is not None else self.review_unit_of(item)
            if unit is None:
                return None
            return self._raise_issue_on(
                session,
                item,
                unit,
                self._not_valid_reason(item),
                ReviewIssueSource.VALIDATION,
            )

    def item_became_valid(
        self,
        item_uid: UUID,
        review_unit: DatabaseItem | None = None,
        session: Session | None = None,
    ) -> bool:
        """Settle what validation raised on an item, and take the unit out of
        the queue if that was the last thing open on it.

        Only what validation raised: an item can be valid and still be
        something a colleague or an import wants looked at.

        Returns
        -------
        bool
            Whether the unit left the queue, which is what a caller working
            through a batch reports on.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return False
            unit = review_unit if review_unit is not None else self.review_unit_of(item)
            for issue in list(
                self._database_service.get_open_issues_for_item(
                    session, item.uid, ReviewIssueSource.VALIDATION
                )
            ):
                self.resolve_issue(issue.uid, session=session)
            session.flush()
            if unit is None:
                return False
            return self.clear_flag_if_nothing_open(unit.uid, session=session)

    def clear_flag_if_nothing_open(
        self,
        unit_uid: UUID,
        session: Session | None = None,
    ) -> bool:
        """Take a review unit out of the queue once nothing is open on it.

        Only one that is flagged: one already reviewed has been answered for,
        and one nobody asked about is not in the queue to leave. What is open
        is what the issues say, so a flag raised without one behind it stays
        until somebody reviews it.

        Returns
        -------
        bool
            Whether the unit left the queue.
        """
        with self._database_service.get_session(session) as session:
            unit = self._database_service.get_optional_item(session, unit_uid)
            if unit is None or unit.review_status != ReviewStatus.FLAGGED:
                return False
            still_open = next(
                iter(self._database_service.get_review_issues(session, unit.uid)),
                None,
            )
            if still_open is not None:
                return False
            unit.review_status = ReviewStatus.NOT_REVIEWED
            unit.review_reason = None
            return True

    @staticmethod
    def _not_valid_reason(item: DatabaseItem) -> str:
        """What is not valid about an item, worded for whoever reads the queue.

        The parts of validity by name rather than a count: which one it is says
        where to go and look, and the item it is about is on the issue already.
        """
        parts = [
            name
            for name, valid in (
                ("attributes", item.valid_attributes),
                ("relations", item.valid_relations),
                ("pseudonym", item.valid_pseudonym),
            )
            if not valid
        ]
        if isinstance(item, DatabaseImage) and item.failed:
            parts.append("image")
        if not parts:
            return "Not valid"
        return f"Not valid: {', '.join(parts)}"

    def raise_imported_issues(
        self,
        result: MetadataSearchResult,
        uid_remap: Mapping[UUID, UUID],
        session: Session,
    ) -> None:
        """Record what the importer found wrong with the unit it handed over.

        Once the items are stored, so that an issue points at the item as it
        ended up rather than at the uid the importer gave it.

        On its own savepoint, for the same reason the check after it is: a unit
        that imported cleanly is worth keeping whether or not what was said
        about it could be written down.
        """
        if not result.issues:
            return
        try:
            with session.begin_nested():
                for issue in result.issues:
                    self.raise_issue(
                        uid_remap.get(issue.item_uid, issue.item_uid),
                        issue.reason,
                        ReviewIssueSource.METADATA_IMPORTER,
                        session=session,
                    )
        except Exception:
            self._logger.error(
                f"Failed to record what the import raised on {result.identifier}",
                exc_info=True,
            )

    def resolve_issue(
        self,
        issue_uid: UUID,
        session: Session | None = None,
    ) -> ReviewIssue | None:
        """Settle an issue, leaving it on record.

        Kept rather than deleted: what was raised and dealt with is part of
        what happened to the case. One already settled keeps when it was.
        """
        with self._database_service.get_session(session) as session:
            issue = self._database_service.get_optional_review_issue(session, issue_uid)
            if issue is None:
                return None
            if issue.resolved_at is None:
                issue.resolved_at = datetime.now()
            return issue.model

    def get_issues(
        self,
        review_unit_uid: UUID,
        include_resolved: bool = False,
        session: Session | None = None,
    ) -> list[ReviewIssue]:
        """What has been raised on a review unit.

        Open ones unless asked otherwise, since what is settled is history
        rather than work.
        """
        with self._database_service.get_session(session) as session:
            return [
                issue.model
                for issue in self._database_service.get_review_issues(
                    session, review_unit_uid, include_resolved
                )
            ]

    def get_non_valid_items(
        self,
        review_unit_uid: UUID,
        session: Session | None = None,
    ) -> list[NonValidItem]:
        """The items under a review unit that are not valid yet.

        What the flag on the unit refers to, for a reviewer to work through.

        Parameters
        ----------
        review_unit_uid: UUID
            The review unit to look under. Anything that is not one holds
            nothing to answer for, and answers with nothing.
        session: Session | None
            Session to look in.

        Returns
        -------
        list[NonValidItem]
            Empty for an item that is not a review unit, and for one where
            everything under it is valid.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, review_unit_uid)
            if item is None:
                return []
            non_valid, _ = self._issues_under(item, session)
            return non_valid

    def _issues_under(
        self,
        item: DatabaseItem,
        session: Session,
    ) -> tuple[list[NonValidItem], int]:
        """What is not as far along as it should be under a review unit, and
        how many items were looked at to find it.

        Empty for an item that is not a review unit: such an item is reviewed
        through the unit that holds it, and answers for nothing on its own.

        Only what is selected counts. Taking an item out of the project is one
        of the two ways of dealing with it — the way an image that matches no
        slide is dealt with, when the slide it belongs to cannot be worked out
        — and an item that is going nowhere cannot be curated into being valid.
        Batch validation reads its items the same way.

        What the unit says its import leaves out is not counted against it
        while the batch is still being filled.
        """
        unit = self._schema_service.review_unit
        if unit is None or unit.schema_uid != item.schema_uid:
            return [], 0
        selected = [
            descendant
            for descendant in self._database_service.walk_item_descendants(item)
            if descendant.selected
        ]
        # What the import leaves for a later step counts against the unit only
        # once that step has run: until the images are in, a reviewer can do
        # nothing about what they would have brought. An item with no batch
        # gives nothing to judge that by, and is held to plain validity.
        expected_completeness = None
        if (
            unit.completeness is not None
            and item.batch is not None
            and item.batch.status < BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
        ):
            expected_completeness = unit.completeness

        issues = [
            NonValidItem(
                uid=descendant.uid,
                identifier=descendant.identifier,
                schema_uid=descendant.schema_uid,
            )
            for descendant in selected
            if not self._is_as_expected(descendant, expected_completeness, session)
        ]
        return sorted(issues, key=lambda issue: issue.identifier), len(selected)

    def _invalid_descendants_reason(
        self,
        item: DatabaseItem,
        session: Session,
    ) -> str | None:
        """What is invalid under a review unit, worded as the reason to flag it.

        ``None`` when everything under it is valid. The panel that lists the
        items says the same thing at length; this is what fits on a queue entry.
        """
        issues, looked_at = self._issues_under(item, session)
        if not issues:
            return None
        shown = ", ".join(issue.identifier for issue in issues[:5])
        return (
            f"{len(issues)} of {looked_at} items are not valid: {shown}"
            f"{', …' if len(issues) > 5 else ''}"
        )

    def _is_as_expected(
        self,
        item: DatabaseItem,
        completeness: MetadataImportCompleteness | None,
        session: Session,
    ) -> bool:
        """Whether an item is as far along as whoever is asking expects.

        Plain validity where nobody said otherwise, which is what a reviewer
        signing a case off is owed.
        """
        if completeness is None:
            return item.valid
        return self._validation_service.item_is_as_complete_as_expected(
            item, completeness, session
        )
