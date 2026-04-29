import React from 'react';
import { motion } from 'framer-motion';
import { MapPin, Award } from 'lucide-react';

const RegionalCards = ({ data }) => {
  const regions = [...new Set(data.map(item => item.Culture))];
  
  const regionalPerformance = regions.map(region => {
    const regionalData = data.filter(item => item.Culture === region);
    const counts = regionalData.reduce((acc, curr) => {
      acc[curr.Winner] = (acc[curr.Winner] || 0) + 1;
      return acc;
    }, {});
    
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const dominantParty = sorted[0][0];
    const total = regionalData.length;
    
    return {
      name: region,
      dominant: dominantParty,
      seats: counts[dominantParty],
      total,
      percentage: Math.round((counts[dominantParty] / total) * 100),
      color: dominantParty === 'SPA' ? '#ef4444' : 
             dominantParty === 'AIADMK+' ? '#10b981' : 
             dominantParty === 'TVK' ? '#f59e0b' : '#94a3b8'
    };
  }).sort((a, b) => b.total - a.total);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1.25rem' }}>
      {regionalPerformance.map((reg, idx) => (
        <motion.div 
          key={reg.name}
          className="card"
          style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column' }}
          whileHover={{ 
            rotateX: 4, 
            rotateY: -4, 
            translateY: -4,
            scale: 1.02,
            transition: { type: "spring", stiffness: 300, damping: 20 }
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>{reg.name}</h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{reg.total} Constituencies</p>
            </div>
            <MapPin size={16} color="var(--border-color)" />
          </div>
          
          <div style={{ marginTop: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Dominant</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: reg.color }}>{reg.dominant}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <span style={{ fontSize: '1.1rem', fontWeight: 800 }}>{reg.seats} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>Seats</span></span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#10b981' }}>{reg.percentage}% Lead</span>
            </div>
            <div style={{ width: '100%', height: '4px', background: 'var(--bg-color)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${reg.percentage}%`, height: '100%', background: reg.color }}></div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default RegionalCards;
