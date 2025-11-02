import React from 'react';
import PropTypes from 'prop-types';

class WordEditDialog extends React.Component {
  constructor(props) {
    super(props);
    this.inputRef = React.createRef();
    this.state = {
      value: props.wordText
    };
  }

  componentDidMount() {
    // Focus input on mount
    if (this.inputRef.current) {
      this.inputRef.current.focus();
      this.inputRef.current.select();
    }
    
    // Add keyboard listeners
    document.addEventListener('keydown', this.handleKeyDown);
  }

  componentWillUnmount() {
    document.removeEventListener('keydown', this.handleKeyDown);
  }

  handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      this.handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      this.props.onCancel();
    }
  };

  handleSave = () => {
    const { value } = this.state;
    this.props.onSave(value.trim());
  };

  handleCancel = () => {
    this.props.onCancel();
  };

  handleChange = (e) => {
    this.setState({ value: e.target.value });
  };

  render() {
    const { wordText } = this.props;
    const { value } = this.state;

    return (
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          background: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '4px',
          padding: '2px 6px',
          margin: '0 2px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={this.inputRef}
          type="text"
          value={value}
          onChange={this.handleChange}
          onBlur={this.handleSave}
          style={{
            border: 'none',
            background: 'transparent',
            padding: '2px 4px',
            fontSize: 'inherit',
            fontFamily: 'inherit',
            minWidth: '60px',
            outline: 'none'
          }}
        />
        <div style={{ display: 'flex', gap: '4px', marginLeft: '8px' }}>
          <button
            onClick={this.handleSave}
            style={{
              background: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '2px',
              padding: '2px 6px',
              cursor: 'pointer',
              fontSize: '11px'
            }}
            title="Enter"
          >
            ✓
          </button>
          <button
            onClick={this.handleCancel}
            style={{
              background: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '2px',
              padding: '2px 6px',
              cursor: 'pointer',
              fontSize: '11px'
            }}
            title="Escape"
          >
            ✕
          </button>
        </div>
      </div>
    );
  }
}

WordEditDialog.propTypes = {
  wordData: PropTypes.object.isRequired,
  wordText: PropTypes.string.isRequired,
  contentState: PropTypes.object.isRequired,
  entityKey: PropTypes.string.isRequired,
  onSave: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired
};

export default WordEditDialog;

