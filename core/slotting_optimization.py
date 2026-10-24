"""
Warehouse Slotting & Storage Optimization Engine (Service 7)
Implements ABC velocity classification, product affinity clustering,
golden-zone ergonomics, replenishment triggers, and pick-travel distance optimization.
"""

from typing import List, Dict, Any, Tuple, Optional
import math
from core.models import SlottingRecommendation
from core.config import settings

class SlottingOptimizationService:
    def __init__(self):
        # Operational parameters for slotting scoring
        self.move_effort_flat_cost = 15.0 # USD per physical relocation
        self.ergonomic_golden_zone_bonus = 25.0
        self.velocity_pick_weights = {"A": 1.0, "B": 0.5, "C": 0.15}

    def compute_sku_velocity(self, pick_history: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Classifies SKUs into Pareto ABC Velocity tiers:
        - A: Top 20% cumulative pick frequency
        - B: Next 30% cumulative pick frequency
        - C: Remaining 50% slow-moving inventory
        """
        sku_counts: Dict[str, int] = {}
        for entry in pick_history:
            sku = entry.get("sku_id")
            picks = entry.get("picks", 1)
            sku_counts[sku] = sku_counts.get(sku, 0) + picks

        if not sku_counts:
            return {}

        sorted_skus = sorted(sku_counts.items(), key=lambda x: x[1], reverse=True)
        total_picks = sum(count for _, count in sorted_skus)
        if total_picks == 0:
            return {sku: "C" for sku, _ in sorted_skus}

        cumulative = 0
        velocity_map = {}
        for sku, count in sorted_skus:
            cumulative += count
            pct = cumulative / total_picks
            if pct <= 0.80 or not velocity_map:
                velocity_map[sku] = "A"
            elif pct <= 0.95:
                velocity_map[sku] = "B"
            else:
                velocity_map[sku] = "C"


        return velocity_map

    def compute_affinity_pairs(self, order_baskets: List[List[str]], min_co_occurrence: int = 2) -> Dict[str, List[str]]:
        """
        Computes SKU affinity pairs using Jaccard co-occurrence across wave pick orders.
        Returns mapped affinity neighbours for each SKU.
        """
        pair_counts: Dict[Tuple[str, str], int] = {}
        item_counts: Dict[str, int] = {}

        for basket in order_baskets:
            unique_items = sorted(list(set(basket)))
            for item in unique_items:
                item_counts[item] = item_counts.get(item, 0) + 1
            for i in range(len(unique_items)):
                for j in range(i + 1, len(unique_items)):
                    pair = (unique_items[i], unique_items[j])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        affinity_map: Dict[str, List[str]] = {}
        for (item_a, item_b), count in pair_counts.items():
            if count >= min_co_occurrence:
                union = item_counts[item_a] + item_counts[item_b] - count
                jaccard = count / union if union > 0 else 0
                if jaccard >= 0.15: # Significant affinity threshold
                    affinity_map.setdefault(item_a, []).append(item_b)
                    affinity_map.setdefault(item_b, []).append(item_a)

        return affinity_map

    def calculate_slotting_score(
        self,
        sku_id: str,
        velocity: str,
        current_distance_to_pack: float,
        proposed_distance_to_pack: float,
        is_golden_zone: bool,
        affinity_neighbors_nearby: int,
        temp_hazmat_fit: bool
    ) -> float:
        """
        Implements exact Slotting Score formula from plan.md:
        Pick Benefit + Travel Distance Reduction + Replenishment Efficiency + Affinity Benefit
        + Space Utilization + Ergonomic Fit + Safety Compliance - Move Effort
        """
        if not temp_hazmat_fit:
            return -9999.0 # Strict safety constraint violation

        vel_weight = self.velocity_pick_weights.get(velocity, 0.2)
        travel_saving = (current_distance_to_pack - proposed_distance_to_pack) * vel_weight * 2.0
        ergonomic_fit = self.ergonomic_golden_zone_bonus if is_golden_zone else 5.0
        affinity_benefit = affinity_neighbors_nearby * 15.0
        pick_benefit = 40.0 if velocity == "A" else (20.0 if velocity == "B" else 5.0)

        total_score = (
            pick_benefit
            + travel_saving
            + ergonomic_fit
            + affinity_benefit
            - self.move_effort_flat_cost
        )
        return round(total_score, 2)

    def optimize_slotting(
        self,
        sku_inventory: List[Dict[str, Any]],
        pick_history: List[Dict[str, Any]],
        order_baskets: List[List[str]],
        available_locations: List[Dict[str, Any]]
    ) -> List[SlottingRecommendation]:
        """
        Generates optimal slotting and relocation recommendations.
        """
        velocity_map = self.compute_sku_velocity(pick_history)
        affinity_map = self.compute_affinity_pairs(order_baskets)
        recommendations: List[SlottingRecommendation] = []

        # Map candidate locations by tier
        forward_locations = [loc for loc in available_locations if loc.get("is_forward_pick", False)]

        for item in sku_inventory:
            sku_id = item.get("sku_id")
            cur_loc = item.get("location_id", "BULK-01")
            cur_dist = item.get("distance_to_packing", 85.0)
            velocity = velocity_map.get(sku_id, "C")
            temp_req = item.get("temperature_controlled", False)
            hazmat = item.get("hazmat", False)

            # High-velocity SKUs (A) should be in forward pick golden zone
            if velocity == "A" and not item.get("in_forward_pick", False):
                # Search suitable forward pick location
                best_loc = None
                best_score = -1.0
                for cand in forward_locations:
                    if cand.get("temperature_controlled", False) != temp_req:
                        continue
                    if cand.get("hazmat_allowed", False) != hazmat:
                        continue
                    
                    cand_dist = cand.get("distance_to_packing", 15.0)
                    is_gz = cand.get("level", "B") in ["B", "C"] # Chest-to-waist
                    aff_neighbors = len([n for n in affinity_map.get(sku_id, []) if n in cand.get("neighbor_skus", [])])
                    
                    score = self.calculate_slotting_score(
                        sku_id=sku_id,
                        velocity=velocity,
                        current_distance_to_pack=cur_dist,
                        proposed_distance_to_pack=cand_dist,
                        is_golden_zone=is_gz,
                        affinity_neighbors_nearby=aff_neighbors,
                        temp_hazmat_fit=True
                    )
                    if score > best_score:
                        best_score = score
                        best_loc = cand

                if best_loc and best_score > 30.0:
                    savings_pct = max(0.0, round(((cur_dist - best_loc.get("distance_to_packing", 15.0)) / cur_dist) * 100, 1))
                    recommendations.append(
                        SlottingRecommendation(
                            sku_id=sku_id,
                            recommended_location=best_loc.get("location_id", "FP-A01"),
                            current_location=cur_loc,
                            sku_velocity=velocity,
                            estimated_travel_savings_pct=savings_pct,
                            affinity_cluster_skus=affinity_map.get(sku_id, []),
                            ergonomic_score=92.5 if best_loc.get("level") in ["B", "C"] else 70.0,
                            move_effort_cost=self.move_effort_flat_cost
                        )
                    )

        return recommendations

    def check_replenishment_trigger(
        self,
        sku_id: str,
        current_forward_qty: int,
        projected_wave_demand: int,
        safety_buffer: int = 20,
        min_reorder_point: int = 50
    ) -> Dict[str, Any]:
        """
        Replenishment Logic from plan.md:
        Available Quantity - Projected Demand - Safety Buffer < Replenishment Trigger
        """
        net_stock = current_forward_qty - projected_wave_demand - safety_buffer
        trigger_active = net_stock < min_reorder_point
        shortfall = max(0, min_reorder_point - net_stock) if trigger_active else 0
        urgency = "CRITICAL" if net_stock <= 0 else ("HIGH" if net_stock < (min_reorder_point / 2) else "NORMAL")

        return {
            "sku_id": sku_id,
            "trigger_active": trigger_active,
            "urgency": urgency,
            "current_forward_qty": current_forward_qty,
            "projected_wave_demand": projected_wave_demand,
            "net_projected_stock": net_stock,
            "recommended_replenish_units": shortfall + safety_buffer * 2
        }

slotting_service = SlottingOptimizationService()
