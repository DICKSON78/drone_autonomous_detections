import React from 'react';
import PropTypes from 'prop-types';
import '../styles/components.css';

/**
 * StatusCard - Displays a single status metric
 */
function StatusCard({ title, value, status = 'normal', icon = '📊' }) {
  const statusClass = `status-card status-${status}`;

  return (
    <div className={statusClass}>
      <div className="card-icon">{icon}</div>
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-value">{value}</p>
      </div>
    </div>
  );
}

StatusCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  status: PropTypes.oneOf(['normal', 'active', 'inactive', 'alert', 'info']),
  icon: PropTypes.string,
};

export default StatusCard;
