import React from 'react';
import { motion } from 'framer-motion';

const LeaderCards = ({ summary }) => {
  const leaders = [
    {
      name: "M. K. Stalin",
      party: "SPA",
      seats: summary.SPA,
      photo: "/assets/spa_leader.png",
      color: "#ef4444"
    },
    {
      name: "E. K. Palaniswami",
      party: "AIADMK+",
      seats: summary['AIADMK+'],
      photo: "/assets/aiadmk_leader.png",
      color: "#10b981"
    },
    {
      name: "Thalapathy Vijay",
      party: "TVK",
      seats: summary.TVK,
      photo: "/assets/tvk_leader.png",
      color: "#f59e0b"
    }
  ].sort((a, b) => b.seats - a.seats);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
      {leaders.map((leader, idx) => (
        <motion.div 
          key={leader.party}
          className="card"
          style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1.25rem' }}
          whileHover={{ 
            rotateX: 5, 
            rotateY: -5, 
            translateY: -4,
            scale: 1.02,
            transition: { type: "spring", stiffness: 300, damping: 20 }
          }}
        >
          <img src={leader.photo} alt={leader.name} className="leader-photo" />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>{leader.name}</h4>
                <span className={`party-badge ${leader.party.replace('+', '').toLowerCase()}`} style={{ fontSize: '0.65rem', padding: '0.2rem 0.5rem', marginTop: '0.25rem', display: 'inline-block' }}>
                  {leader.party}
                </span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: leader.color, lineHeight: 1 }}>{leader.seats}</div>
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '0.25rem' }}>Seats</div>
              </div>
            </div>
            {/* Minimal progress bar */}
            <div style={{ width: '100%', height: '4px', background: 'var(--bg-color)', borderRadius: '2px', marginTop: '0.75rem', overflow: 'hidden' }}>
              <div style={{ width: `${(leader.seats / 234) * 100}%`, height: '100%', background: leader.color }}></div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default LeaderCards;
