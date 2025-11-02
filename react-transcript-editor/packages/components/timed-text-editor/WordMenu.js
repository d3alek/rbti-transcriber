import React from 'react';
import PropTypes from 'prop-types';

class WordMenu extends React.Component {
  constructor(props) {
    super(props);
    this.menuRef = React.createRef();
  }

  componentDidMount() {
    // Position the menu near the clicked word
    if (this.menuRef.current && this.props.anchorElement) {
      const rect = this.props.anchorElement.getBoundingClientRect();
      const menu = this.menuRef.current;
      menu.style.position = 'fixed';
      menu.style.left = `${rect.left}px`;
      menu.style.top = `${rect.bottom + 5}px`;
      menu.style.zIndex = '1000';
      
      // Add click outside handler
      document.addEventListener('click', this.handleClickOutside);
    }
  }

  componentWillUnmount() {
    document.removeEventListener('click', this.handleClickOutside);
  }

  handleClickOutside = (e) => {
    // Don't close if click is on the menu or the anchor element
    if (this.menuRef.current && !this.menuRef.current.contains(e.target)) {
      // Check if the click is on the anchor word element
      if (this.props.anchorElement && this.props.anchorElement.contains(e.target)) {
        return;
      }
      this.props.onClose();
    }
  };

  render() {
    return (
      <div
        ref={this.menuRef}
        style={{
          background: 'white',
          border: '1px solid #ccc',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          padding: '4px 0',
          minWidth: '120px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          style={{
            width: '100%',
            textAlign: 'left',
            padding: '8px 16px',
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            fontSize: '14px'
          }}
          onClick={(e) => {
            e.stopPropagation();
            this.props.onPlay();
          }}
          onMouseEnter={(e) => (e.target.style.background = '#f0f0f0')}
          onMouseLeave={(e) => (e.target.style.background = 'transparent')}
        >
          ▶ Play
        </button>
        <button
          style={{
            width: '100%',
            textAlign: 'left',
            padding: '8px 16px',
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            fontSize: '14px',
            borderTop: '1px solid #eee'
          }}
          onClick={(e) => {
            e.stopPropagation();
            this.props.onCorrect();
          }}
          onMouseEnter={(e) => (e.target.style.background = '#f0f0f0')}
          onMouseLeave={(e) => (e.target.style.background = 'transparent')}
        >
          ✎ Correct
        </button>
      </div>
    );
  }
}

WordMenu.propTypes = {
  wordData: PropTypes.object.isRequired,
  wordText: PropTypes.string.isRequired,
  onPlay: PropTypes.func.isRequired,
  onCorrect: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  anchorElement: PropTypes.object
};

export default WordMenu;

