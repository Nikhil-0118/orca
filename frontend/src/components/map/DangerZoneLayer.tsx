import React from 'react';
import { DangerZone } from '../../types/map.types';

interface DangerZoneLayerProps {
  zones: DangerZone[];
  visible: boolean;
}

export const DangerZoneLayer: React.FC<DangerZoneLayerProps> = ({ zones, visible }) => {
  if (!visible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Visual representation of geofenced danger / boundary zones */}
      {zones.map((zone) => (
        <div
          key={zone.zone_id}
          className="absolute border border-red-500/80 bg-red-500/20 rounded-lg p-2 text-[10px] text-red-200 font-mono"
          style={{ top: '20%', left: '25%', width: '120px', height: '100px' }}
        >
          <span>⚠️ {zone.title}</span>
        </div>
      ))}
    </div>
  );
};
