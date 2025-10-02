"""Slot consolidation service to merge overlapping time slots intelligently."""

from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
from app.models import TimeSlot, CourtAvailability


class SlotConsolidationService:
    """Service to consolidate overlapping time slots into optimal notifications."""
    
    def consolidate_court_availability(self, courts: List[CourtAvailability]) -> List[CourtAvailability]:
        """
        Consolidate overlapping and adjacent time slots for each court.
        Returns courts with consolidated, non-overlapping slots.
        """
        consolidated_courts = []
        
        for court in courts:
            # Get all available time slots
            available_slots = [slot for slot in court.time_slots if slot.available]
            
            if not available_slots:
                # No available slots, keep the court as is
                consolidated_courts.append(court)
                continue
            
            # Step 1: Consolidate overlapping slots
            overlapping_consolidated = self._consolidate_time_slots(available_slots)
            
            # Step 2: Consolidate adjacent slots
            fully_consolidated = self._consolidate_adjacent_slots(overlapping_consolidated)
            
            # Create new court with fully consolidated slots
            consolidated_court = CourtAvailability(
                court_id=court.court_id,
                court_name=court.court_name,
                time_slots=fully_consolidated
            )
            consolidated_courts.append(consolidated_court)
        
        return consolidated_courts
    
    def _consolidate_time_slots(self, slots: List[TimeSlot]) -> List[TimeSlot]:
        """
        Consolidate overlapping time slots into the longest possible slots.
        
        Algorithm:
        1. Sort slots by start time
        2. Group overlapping slots
        3. For each group, create the longest possible slot
        4. Return consolidated slots
        """
        if not slots:
            return []
        
        # Sort slots by start time
        sorted_slots = sorted(slots, key=lambda s: s.start_time)
        
        # Group overlapping slots
        slot_groups = self._group_overlapping_slots(sorted_slots)
        
        # Consolidate each group
        consolidated_slots = []
        for group in slot_groups:
            consolidated_slot = self._merge_slot_group(group)
            consolidated_slots.append(consolidated_slot)
        
        return consolidated_slots
    
    def _group_overlapping_slots(self, sorted_slots: List[TimeSlot]) -> List[List[TimeSlot]]:
        """Group slots that overlap with each other."""
        if not sorted_slots:
            return []
        
        groups = []
        current_group = [sorted_slots[0]]
        
        for i in range(1, len(sorted_slots)):
            current_slot = sorted_slots[i]
            last_slot_in_group = current_group[-1]
            
            # Check if current slot overlaps with the last slot in current group
            if self._slots_overlap(last_slot_in_group, current_slot):
                current_group.append(current_slot)
            else:
                # No overlap, start a new group
                groups.append(current_group)
                current_group = [current_slot]
        
        # Add the last group
        groups.append(current_group)
        
        return groups
    
    def _slots_overlap(self, slot1: TimeSlot, slot2: TimeSlot) -> bool:
        """Check if two time slots overlap."""
        # Two slots overlap if one starts before the other ends
        return (slot1.start_time < slot2.end_time and 
                slot2.start_time < slot1.end_time)
    
    def _merge_slot_group(self, group: List[TimeSlot]) -> TimeSlot:
        """Merge a group of overlapping slots into one optimal slot."""
        if not group:
            raise ValueError("Cannot merge empty slot group")
        
        if len(group) == 1:
            return group[0]
        
        # Find the earliest start time and latest end time
        start_time = min(slot.start_time for slot in group)
        end_time = max(slot.end_time for slot in group)
        
        # Calculate average price (or use the lowest price)
        prices = [slot.price for slot in group if slot.price is not None]
        avg_price = sum(prices) / len(prices) if prices else None
        
        # Use the currency from the first slot
        currency = group[0].currency
        
        # Create consolidated slot
        consolidated_slot = TimeSlot(
            start_time=start_time,
            end_time=end_time,
            available=True,
            price=avg_price,
            currency=currency
        )
        
        return consolidated_slot
    
    def _consolidate_adjacent_slots(self, slots: List[TimeSlot]) -> List[TimeSlot]:
        """
        Consolidate adjacent (non-overlapping) time slots into longer slots.
        
        Algorithm:
        1. Sort slots by start time
        2. Find chains of adjacent slots
        3. Merge each chain into one optimal slot
        """
        if not slots:
            return []
        
        # Sort slots by start time
        sorted_slots = sorted(slots, key=lambda s: s.start_time)
        
        # Group adjacent slots
        adjacent_groups = self._group_adjacent_slots(sorted_slots)
        
        # Consolidate each group
        consolidated_slots = []
        for group in adjacent_groups:
            if len(group) == 1:
                # Single slot, no consolidation needed
                consolidated_slots.append(group[0])
            else:
                # Multiple adjacent slots, consolidate them
                consolidated_slot = self._merge_adjacent_group(group)
                consolidated_slots.append(consolidated_slot)
        
        return consolidated_slots
    
    def _group_adjacent_slots(self, sorted_slots: List[TimeSlot]) -> List[List[TimeSlot]]:
        """Group slots that are adjacent to each other."""
        if not sorted_slots:
            return []
        
        groups = []
        current_group = [sorted_slots[0]]
        
        for i in range(1, len(sorted_slots)):
            current_slot = sorted_slots[i]
            last_slot_in_group = current_group[-1]
            
            # Check if current slot is adjacent to the last slot in current group
            if self._slots_are_adjacent(last_slot_in_group, current_slot):
                current_group.append(current_slot)
            else:
                # Not adjacent, start a new group
                groups.append(current_group)
                current_group = [current_slot]
        
        # Add the last group
        groups.append(current_group)
        
        return groups
    
    def _slots_are_adjacent(self, slot1: TimeSlot, slot2: TimeSlot) -> bool:
        """Check if two time slots are adjacent (one ends when the other starts)."""
        # Also check if they overlap slightly (within 1 minute) to handle edge cases
        time_diff = abs((slot2.start_time - slot1.end_time).total_seconds())
        return time_diff <= 60  # Allow up to 1 minute gap or overlap
    
    def _merge_adjacent_group(self, group: List[TimeSlot]) -> TimeSlot:
        """Merge a group of adjacent slots into one optimal slot."""
        if not group:
            raise ValueError("Cannot merge empty adjacent group")
        
        if len(group) == 1:
            return group[0]
        
        # Find the earliest start time and latest end time
        start_time = min(slot.start_time for slot in group)
        end_time = max(slot.end_time for slot in group)
        
        # Calculate average price (or use the lowest price)
        prices = [slot.price for slot in group if slot.price is not None]
        avg_price = sum(prices) / len(prices) if prices else None
        
        # Use the currency from the first slot
        currency = group[0].currency
        
        # Create consolidated slot
        consolidated_slot = TimeSlot(
            start_time=start_time,
            end_time=end_time,
            available=True,
            price=avg_price,
            currency=currency
        )
        
        return consolidated_slot
    
    def filter_by_minimum_duration(
        self, 
        courts: List[CourtAvailability], 
        minimum_duration_minutes: int
    ) -> List[CourtAvailability]:
        """Filter courts to only include slots meeting minimum duration requirement."""
        filtered_courts = []
        
        for court in courts:
            filtered_slots = []
            for slot in court.time_slots:
                if slot.available:
                    duration_minutes = (slot.end_time - slot.start_time).total_seconds() / 60
                    if duration_minutes >= minimum_duration_minutes:
                        filtered_slots.append(slot)
            
            if filtered_slots:
                filtered_court = CourtAvailability(
                    court_id=court.court_id,
                    court_name=court.court_name,
                    time_slots=filtered_slots
                )
                filtered_courts.append(filtered_court)
        
        return filtered_courts
    
    def get_consolidation_stats(self, original_courts: List[CourtAvailability], 
                              consolidated_courts: List[CourtAvailability]) -> Dict:
        """Get statistics about the consolidation process."""
        original_slots = sum(len([s for s in court.time_slots if s.available]) 
                           for court in original_courts)
        consolidated_slots = sum(len([s for s in court.time_slots if s.available]) 
                               for court in consolidated_courts)
        
        return {
            "original_slots": original_slots,
            "consolidated_slots": consolidated_slots,
            "slots_eliminated": original_slots - consolidated_slots,
            "consolidation_ratio": consolidated_slots / original_slots if original_slots > 0 else 0
        }


# Global slot consolidation service instance
slot_consolidation_service = SlotConsolidationService()
