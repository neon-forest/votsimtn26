import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Map as MapIcon, Info, Crosshair } from 'lucide-react';

// Geographically approximate centers for districts in a 300x400 coordinate space
const districtCoords = {
  'Chennai': { x: 265, y: 45 },
  'Thiruvallur': { x: 250, y: 30 },
  'Kancheepuram': { x: 240, y: 65 },
  'Chengalpattu': { x: 255, y: 80 },
  'Vellore': { x: 210, y: 45 },
  'Ranipet': { x: 225, y: 50 },
  'Tirupathur': { x: 195, y: 60 },
  'Krishnagiri': { x: 160, y: 60 },
  'Dharmapuri': { x: 170, y: 90 },
  'Salem': { x: 165, y: 130 },
  'Erode': { x: 130, y: 135 },
  'Nilgiris': { x: 90, y: 130 },
  'Coimbatore': { x: 105, y: 175 },
  'Tiruppur': { x: 135, y: 170 },
  'Namakkal': { x: 160, y: 155 },
  'Karur': { x: 165, y: 180 },
  'Tiruchirappalli': { x: 190, y: 180 },
  'Perambalur': { x: 205, y: 155 },
  'Ariyalur': { x: 225, y: 165 },
  'Cuddalore': { x: 245, y: 145 },
  'Viluppuram': { x: 235, y: 110 },
  'Kallakurichi': { x: 210, y: 120 },
  'Tiruvannamalai': { x: 215, y: 85 },
  'Nagapattinam': { x: 265, y: 205 },
  'Mayiladuthurai': { x: 260, y: 185 },
  'Thanjavur': { x: 235, y: 205 },
  'Thiruvarur': { x: 255, y: 215 },
  'Pudukkottai': { x: 215, y: 230 },
  'Sivaganga': { x: 200, y: 255 },
  'Madurai': { x: 175, y: 245 },
  'Theni': { x: 135, y: 255 },
  'Dindigul': { x: 155, y: 215 },
  'Virudhunagar': { x: 165, y: 285 },
  'Ramanathapuram': { x: 225, y: 300 },
  'Thoothukudi': { x: 185, y: 335 },
  'Tenkasi': { x: 135, y: 335 },
  'Tirunelveli': { x: 155, y: 355 },
  'Kanniyakumari': { x: 145, y: 385 },
};

const TNMap = ({ data }) => {
  const points = useMemo(() => {
    if (!data) return [];
    
    const districtCounts = {};
    
    return data.map((row) => {
      const district = row.District || 'Chennai';
      const coords = districtCoords[district] || districtCoords['Chennai'];
      
      if (!districtCounts[district]) districtCounts[district] = 0;
      districtCounts[district]++;
      
      // Better jitter: Golden ratio spiral for organic distribution within the district cluster
      const angle = (districtCounts[district] * 137.5) * (Math.PI / 180);
      const radius = Math.sqrt(districtCounts[district]) * 4.5;
      
      return {
        id: row.Constituency,
        x: coords.x + Math.cos(angle) * radius,
        y: coords.y + Math.sin(angle) * radius,
        party: row.Winner,
        color: row.Winner === 'SPA' ? 'var(--color-spa)' : 
               row.Winner === 'AIADMK+' ? 'var(--color-aiadmk)' : 
               row.Winner === 'TVK' ? 'var(--color-tvk)' : 'var(--color-others)',
        name: row.Constituency,
        district: district
      };
    });
  }, [data]);

  // A more detailed TN outline path
  const tnPath = "M 240,20 L 270,35 L 285,60 L 265,110 L 275,160 L 290,200 L 270,235 L 245,305 L 180,380 L 140,395 L 125,380 L 130,340 L 105,320 L 85,250 L 95,180 L 70,140 L 95,90 L 140,55 L 190,35 Z";

  return (
    <div className="glass-panel" style={{ padding: '2rem', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', fontSize: '1.25rem', fontWeight: 600 }}>
          <MapIcon size={20} color="var(--color-turmeric-gold)" /> Electoral Topography
        </h3>
        <div style={{ fontSize: '0.7rem', color: 'var(--color-turmeric-gold)', opacity: 0.8, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Crosshair size={12} /> Live Simulation Data
        </div>
      </div>
      
      <div style={{ 
        position: 'relative', 
        flex: 1, 
        minHeight: '450px', 
        width: '100%', 
        background: 'radial-gradient(circle at center, rgba(30,30,40,1) 0%, rgba(10,10,15,1) 100%)', 
        borderRadius: '16px', 
        padding: '2rem',
        boxShadow: 'inset 0 0 40px rgba(0,0,0,0.5)',
        border: '1px solid rgba(255,255,255,0.05)'
      }}>
        <svg viewBox="0 0 300 410" style={{ width: '100%', height: '100%', filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.5))' }}>
          {/* Detailed TN Outline */}
          <path 
            d={tnPath}
            fill="rgba(255,255,255,0.01)"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          
          {/* Subtle Grid Lines */}
          <g opacity="0.03">
            {[...Array(10)].map((_, i) => (
              <line key={`v-${i}`} x1={i * 30} y1="0" x2={i * 30} y2="410" stroke="#fff" strokeWidth="0.5" />
            ))}
            {[...Array(14)].map((_, i) => (
              <line key={`h-${i}`} x1="0" y1={i * 30} x2="300" y2={i * 30} stroke="#fff" strokeWidth="0.5" />
            ))}
          </g>
          
          {/* Seat Points */}
          {points.map((pt, idx) => (
            <motion.g key={pt.id + idx}>
              {/* Glow Layer */}
              <circle
                cx={pt.x}
                cy={pt.y}
                r={2.5}
                fill={pt.color}
                opacity="0.15"
                style={{ filter: 'blur(2px)' }}
              />
              {/* Main Point */}
              <motion.circle
                cx={pt.x}
                cy={pt.y}
                r={2.2}
                fill={pt.color}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 0.9 }}
                whileHover={{ scale: 3, opacity: 1, stroke: '#fff', strokeWidth: 0.8 }}
                transition={{ delay: (idx % 234) * 0.005, type: 'spring', stiffness: 200 }}
                style={{ cursor: 'pointer' }}
              >
                <title>{pt.name} ({pt.district})\nWinner: {pt.party}</title>
              </motion.circle>
            </motion.g>
          ))}
        </svg>

        {/* Legend */}
        <div style={{ position: 'absolute', bottom: '1.5rem', right: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.6rem', padding: '0.8rem', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
          {['SPA', 'AIADMK+', 'TVK', 'Others'].map(p => (
            <div key={p} style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', fontSize: '0.75rem', fontWeight: 500 }}>
              <div style={{ 
                width: '10px', 
                height: '10px', 
                borderRadius: '50%', 
                background: p === 'SPA' ? 'var(--color-spa)' : p === 'AIADMK+' ? 'var(--color-aiadmk)' : p === 'TVK' ? 'var(--color-tvk)' : 'var(--color-others)',
                boxShadow: `0 0 8px ${p === 'SPA' ? 'var(--color-spa)' : p === 'AIADMK+' ? 'var(--color-aiadmk)' : p === 'TVK' ? 'var(--color-tvk)' : 'var(--color-others)'}`
              }}></div>
              <span style={{ opacity: 0.9 }}>{p}</span>
            </div>
          ))}
        </div>
      </div>

      <p style={{ marginTop: '1.2rem', fontSize: '0.8rem', opacity: 0.6, textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--color-turmeric-gold)' }}>
        <Info size={14} /> 234 Micro-Clusters representing individual assembly constituencies
      </p>
    </div>
  );
};

export default TNMap;
