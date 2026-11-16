"""Reference solution for Problem 2: Banking ledger."""

from __future__ import annotations

import heapq
import math
from bisect import bisect_right
from dataclasses import dataclass, field

# Design in brief
# ---------------
# - Every public method starts with _advance(timestamp). It runs the scheduled payments that
#   are due, in (due, seq) order, BEFORE the method does its own work. That is the rule the
#   problem states, and putting it in one place means no method can forget it.
# - A payment is applied at its due time, not at the later call that notices it, and its
#   balance change is logged at that due time. That is what makes get_balance correct.
# - Each Account keeps an append-only history of (timestamp, balance), so get_balance is a
#   binary search instead of a replay.
# - A public id maps to an Account object. Merged-away accounts stay in `incarnations`, so
#   their history can still be queried, and re-creating an id builds a brand-new Account.


@dataclass
class Account:
    created_at: int
    # The account exists for created_at <= t < deleted_at; math.inf while it is still alive.
    deleted_at: float = math.inf
    balance: int = 0
    # Money sent out: transfers and executed scheduled payments. top_spenders ranks by this.
    outgoing: int = 0
    # Appended to on every balance change, in time order, so it stays sorted for bisect.
    history: list[tuple[int, int]] = field(default_factory=list)  # (timestamp, balance)


# order=True gives the heap its ordering, and only the fields that are not `compare=False` take
# part in it: that is (due, seq). The heap pops the earliest due first and breaks ties by
# creation order, exactly the order the problem requires payments to run in.
@dataclass(order=True)
class Payment:
    due: int
    seq: int  # creation order; also the number in "paymentN"
    payment_id: str = field(compare=False)
    # The Account object, not its id: merge_accounts re-points this to the target. That is safe
    # while the payment sits in the heap, because `account` is not part of the ordering.
    account: Account = field(compare=False)
    amount: int = field(compare=False)
    status: str = field(default="pending", compare=False)  # pending/done/skipped/cancelled


class Bank:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}  # live accounts only
        self.incarnations: dict[str, list[Account]] = {}  # every account that ever used an id
        self.queue: list[Payment] = []  # heap ordered by (due, seq)
        # payment_id -> Payment, for cancel_payment. Its size also numbers the next payment,
        # because ids are never reused.
        self.payments: dict[str, Payment] = {}

    # -- helpers: time engine and the only code that changes a balance -----------------
    def _advance(self, timestamp: int) -> None:
        # Run every payment due at or before `timestamp`. The heap hands them over in
        # (due, seq) order, which is also the order they must be applied in.
        while self.queue and self.queue[0].due <= timestamp:
            payment = heapq.heappop(self.queue)
            if payment.status != "pending":
                # Cancelled payments are not removed from the heap when cancelled (removing from
                # the middle of a heap is awkward); they are dropped here when they surface.
                continue  # cancelled: lazy deletion
            account = payment.account
            if account.balance >= payment.amount:
                # Logged at the payment's DUE time, not at `timestamp`, so a later get_balance
                # for any time_at sees the withdrawal at the moment it really happened.
                self._set_balance(account, payment.due, account.balance - payment.amount)
                account.outgoing += payment.amount
                payment.status = "done"
            else:
                # Would overdraw: skipped, never retried, and it does NOT count as outgoing.
                payment.status = "skipped"

    def _set_balance(self, account: Account, timestamp: int, balance: int) -> None:
        # The only place a balance changes. Updating it and logging history together means
        # the history can never miss a change.
        account.balance = balance
        account.history.append((timestamp, balance))

    # -- Level 1 ------------------------------------------------------------------------
    def create_account(self, timestamp: int, account_id: str) -> bool:
        """Create a new account; return False if the account already exists."""
        # Every public method starts with _advance, even ones that do not touch payments:
        # one uniform rule is easier to get right than a per-method judgement call.
        self._advance(timestamp)
        if account_id in self.accounts:
            return False
        account = Account(created_at=timestamp)
        # The first history entry sits at the creation time, so get_balance always finds an
        # entry for any time_at inside the account's lifetime.
        self._set_balance(account, timestamp, 0)
        self.accounts[account_id] = account
        # Newest last: get_balance scans from the newest incarnation backwards.
        self.incarnations.setdefault(account_id, []).append(account)
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        """Add amount to the account and return the new balance, or None if it doesn't exist."""
        self._advance(timestamp)
        account = self.accounts.get(account_id)
        if account is None:
            return None
        self._set_balance(account, timestamp, account.balance + amount)
        return account.balance

    def transfer(self, timestamp: int, from_id: str, to_id: str, amount: int) -> int | None:
        """Move amount from from_id to to_id and return the sender's new balance, or None."""
        self._advance(timestamp)
        sender, receiver = self.accounts.get(from_id), self.accounts.get(to_id)
        # Reject an unknown account, a transfer to oneself, or insufficient funds. Nothing has
        # been changed yet, so every failure leaves the bank untouched.
        if sender is None or receiver is None or from_id == to_id or sender.balance < amount:
            return None
        self._set_balance(sender, timestamp, sender.balance - amount)
        self._set_balance(receiver, timestamp, receiver.balance + amount)
        sender.outgoing += amount  # only the sender "spends"; the receiver's total is unchanged
        return sender.balance

    # -- Level 2 ------------------------------------------------------------------------
    def top_spenders(self, timestamp: int, n: int) -> str:
        """Return the top n accounts by total outgoing money, as "id(total), ..."."""
        self._advance(timestamp)
        # Only live accounts are ranked, so a merged-away account drops out (its total moved to
        # the merge target). Outgoing descending, then id ascending.
        ranked = sorted(self.accounts.items(), key=lambda item: (-item[1].outgoing, item[0]))
        return ", ".join(f"{account_id}({acc.outgoing})" for account_id, acc in ranked[:n])

    # -- Level 3 ------------------------------------------------------------------------
    def schedule_payment(
        self, timestamp: int, account_id: str, amount: int, delay: int
    ) -> str | None:
        """Schedule a withdrawal at timestamp + delay; return "paymentN", or None."""
        self._advance(timestamp)
        account = self.accounts.get(account_id)
        if account is None:
            return None
        # A failed schedule never creates a Payment, so it never consumes an id.
        seq = len(self.payments) + 1
        payment = Payment(timestamp + delay, seq, f"payment{seq}", account, amount)
        self.payments[payment.payment_id] = payment
        # This only registers the payment. No money moves until _advance reaches its due time.
        heapq.heappush(self.queue, payment)
        return payment.payment_id

    def cancel_payment(self, timestamp: int, account_id: str, payment_id: str) -> bool:
        """Cancel a pending payment of this account; return False if that isn't possible."""
        self._advance(timestamp)
        payment = self.payments.get(payment_id)
        # Only a payment that has not run, been skipped or been cancelled can be cancelled.
        if payment is None or payment.status != "pending":
            return False
        # Compare with the account's CURRENT object. This also covers a missing account
        # (get returns None, which is never `payment.account`), and after a merge the payment
        # belongs to the target, so only the target's id works.
        if payment.account is not self.accounts.get(account_id):
            return False  # missing account, or the payment belongs to another account
        # Marking it is enough: _advance discards cancelled payments when they come due.
        payment.status = "cancelled"
        return True

    # -- Level 4 ------------------------------------------------------------------------
    def merge_accounts(self, timestamp: int, target_id: str, source_id: str) -> bool:
        """Move source's balance, outgoing and pending payments to target, then delete source."""
        # _advance ran first, so payments due up to now have already hit the OLD accounts.
        self._advance(timestamp)
        target, source = self.accounts.get(target_id), self.accounts.get(source_id)
        if target is None or source is None or target_id == source_id:
            return False
        del self.accounts[source_id]  # the id is free to be re-created as a brand-new account
        # Pending payments follow the money: re-point them from the source to the target.
        for payment in self.queue:
            if payment.account is source:
                payment.account = target
        # Totals carry over, so top_spenders ranks the merged account by its combined outgoing.
        target.outgoing += source.outgoing
        # One history entry at the merge time. The target's earlier entries are not touched, so
        # its earlier balances stay unchanged.
        self._set_balance(target, timestamp, target.balance + source.balance)
        # Close the source's lifetime. It stays in `incarnations`, so get_balance still answers
        # for times before the merge.
        source.deleted_at = timestamp
        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        """Return the account's balance right after all operations at time_at, or None."""
        self._advance(timestamp)
        # An id can be deleted by a merge and re-created, and each Account has its own history.
        # So find the incarnation that was alive at time_at, newest first.
        for account in reversed(self.incarnations.get(account_id, [])):
            # Half-open lifetime: alive from created_at up to, but not including, deleted_at.
            if account.created_at <= time_at < account.deleted_at:
                # bisect_right returns the position after the last entry with ts <= time_at, so
                # the entry just before it is the balance after ALL operations at time_at.
                # There is always one: history starts at created_at and time_at >= created_at.
                i = bisect_right(account.history, time_at, key=lambda entry: entry[0])
                return account.history[i - 1][1]
        return None
