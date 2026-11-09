"""Mutant: top_spenders sorts by total only, so ties keep account creation order instead of id ascending."""

from __future__ import annotations

import heapq
import math
from bisect import bisect_right
from dataclasses import dataclass, field


@dataclass
class Account:
    created_at: int
    deleted_at: float = math.inf
    balance: int = 0
    outgoing: int = 0
    history: list[tuple[int, int]] = field(default_factory=list)  # (timestamp, balance)


@dataclass(order=True)
class Payment:
    due: int
    seq: int
    payment_id: str = field(compare=False)
    account: Account = field(compare=False)
    amount: int = field(compare=False)
    status: str = field(default="pending", compare=False)  # pending/done/skipped/cancelled


class Bank:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}  # live accounts only
        self.incarnations: dict[str, list[Account]] = {}  # every account that ever used an id
        self.queue: list[Payment] = []  # heap ordered by (due, seq)
        self.payments: dict[str, Payment] = {}

    # -- helpers: time engine and the only code that changes a balance -----------------
    def _advance(self, timestamp: int) -> None:
        while self.queue and self.queue[0].due <= timestamp:
            payment = heapq.heappop(self.queue)
            if payment.status != "pending":
                continue  # cancelled: lazy deletion
            account = payment.account
            if account.balance >= payment.amount:
                self._set_balance(account, payment.due, account.balance - payment.amount)
                account.outgoing += payment.amount
                payment.status = "done"
            else:
                payment.status = "skipped"

    def _set_balance(self, account: Account, timestamp: int, balance: int) -> None:
        account.balance = balance
        account.history.append((timestamp, balance))

    # -- Level 1 ------------------------------------------------------------------------
    def create_account(self, timestamp: int, account_id: str) -> bool:
        """Create a new account; return False if the account already exists."""
        self._advance(timestamp)
        if account_id in self.accounts:
            return False
        account = Account(created_at=timestamp)
        self._set_balance(account, timestamp, 0)
        self.accounts[account_id] = account
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
        if sender is None or receiver is None or from_id == to_id or sender.balance < amount:
            return None
        self._set_balance(sender, timestamp, sender.balance - amount)
        self._set_balance(receiver, timestamp, receiver.balance + amount)
        sender.outgoing += amount
        return sender.balance

    # -- Level 2 ------------------------------------------------------------------------
    def top_spenders(self, timestamp: int, n: int) -> str:
        """Return the top n accounts by total outgoing money, as "id(total), ..."."""
        self._advance(timestamp)
        ranked = sorted(self.accounts.items(), key=lambda item: -item[1].outgoing)
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
        seq = len(self.payments) + 1
        payment = Payment(timestamp + delay, seq, f"payment{seq}", account, amount)
        self.payments[payment.payment_id] = payment
        heapq.heappush(self.queue, payment)
        return payment.payment_id

    def cancel_payment(self, timestamp: int, account_id: str, payment_id: str) -> bool:
        """Cancel a pending payment of this account; return False if that isn't possible."""
        self._advance(timestamp)
        payment = self.payments.get(payment_id)
        if payment is None or payment.status != "pending":
            return False
        if payment.account is not self.accounts.get(account_id):
            return False  # missing account, or the payment belongs to another account
        payment.status = "cancelled"
        return True

    # -- Level 4 ------------------------------------------------------------------------
    def merge_accounts(self, timestamp: int, target_id: str, source_id: str) -> bool:
        """Move source's balance, outgoing and pending payments to target, then delete source."""
        self._advance(timestamp)
        target, source = self.accounts.get(target_id), self.accounts.get(source_id)
        if target is None or source is None or target_id == source_id:
            return False
        del self.accounts[source_id]
        for payment in self.queue:
            if payment.account is source:
                payment.account = target
        target.outgoing += source.outgoing
        self._set_balance(target, timestamp, target.balance + source.balance)
        source.deleted_at = timestamp
        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        """Return the account's balance right after all operations at time_at, or None."""
        self._advance(timestamp)
        for account in reversed(self.incarnations.get(account_id, [])):
            if account.created_at <= time_at < account.deleted_at:
                i = bisect_right(account.history, time_at, key=lambda entry: entry[0])
                return account.history[i - 1][1]
        return None
