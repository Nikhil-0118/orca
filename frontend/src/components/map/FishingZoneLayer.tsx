import React from 'react';
import { FishingZone } from '../../types/map.types';

interface FishingZoneLayerProps {
  zones: FishingZone[];
  visible: boolean;
}

export const FishingZoneLayer: React.FC<FishingZoneLayerProps> = ({ zones, visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Visual representation of high-yield PFZ zones */}
      {zones.map((zone) => (
        <div
          key={zone.zone_id}
          className="absolute border border-emerald-400/80 bg-emerald-500/15 rounded-xl p-2 text-[10px] text-emerald-300 font-mono shadow-lg shadow-emerald-950/50"
          style={{ top: '45%', left: '50%', width: '140px', height: '110px' }}
        >
          <div className="font-bold">🐟 PFZ Advisory</div>
          <div>Depth: {zone.depth_meters}m</div>
          <div>Score: {(zone.confidence_score * 100).toFixed(0)}%</div>
        </div>
      ))}
    </div>
  );
};
