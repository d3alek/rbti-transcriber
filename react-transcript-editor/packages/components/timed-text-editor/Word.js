import React, { Component } from 'react';
import PropTypes from 'prop-types';
import WordMenu from './WordMenu';
import WordEditDialog from './WordEditDialog';

class Word extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showMenu: false,
      editing: false
    };
    this.wordRef = React.createRef();
  }

  shouldComponentUpdate(nextProps, nextState) {
    if ( nextProps.decoratedText !== this.props.decoratedText) {
      return true;
    }
    
    if (this.state.showMenu !== nextState.showMenu || 
        this.state.editing !== nextState.editing) {
      return true;
    }

    return false;
  }

  handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (this.state.editing) {
      return;
    }
    
    this.setState({ showMenu: true });
  };
  

  handleMenuClose = () => {
    this.setState({ showMenu: false });
  };

  handleEdit = () => {
    this.setState({ editing: true, showMenu: false });
  };

  handleEditComplete = () => {
    this.setState({ editing: false });
  };

  generateConfidence = (data) => {
    // handling edge case where confidence score not present
    if (data.confidence) {
      return data.confidence > 0.6 ? 'high' : 'low';
    }

    return 'high';
  }

  generatePreviousTimes = (data) => {
    let prevTimes = '';

    for (let i = 0; i < data.start; i++) {
      prevTimes += `${ i } `;
    }

    if (data.start % 1 > 0) {
      // Find the closest quarter-second to the current time, for more dynamic results
      const dec = Math.floor((data.start % 1) * 4.0) / 4.0;
      prevTimes += ` ${ Math.floor(data.start) + dec }`;
    }

    return prevTimes;
  }

  render() {
    const data = this.props.entityKey
      ? this.props.contentState.getEntity(this.props.entityKey).getData()
      : {};

    const { showMenu, editing } = this.state;
    
    return (
      <span
        ref={this.wordRef}
        data-start={ data.start }
        data-end={ data.end }
        data-confidence = { this.generateConfidence(data) }
        data-prev-times = { this.generatePreviousTimes(data) }
        data-entity-key={ data.key }
        className="Word"
        onClick={this.handleClick}
        style={{ position: 'relative', display: editing ? 'inline-flex' : 'inline' }}>
        {this.props.children}
        {showMenu && !editing && (
          <WordMenu
            wordData={data}
            wordText={this.props.decoratedText}
            onPlay={() => {
              this.handleMenuClose();
              // Trigger word click via data attribute (double-click behavior)
              const event = new CustomEvent('word-play', { detail: { start: data.start } });
              window.dispatchEvent(event);
            }}
            onCorrect={this.handleEdit}
            onClose={this.handleMenuClose}
            anchorElement={this.wordRef.current}
          />
        )}
        {editing && (
          <WordEditDialog
            wordData={data}
            wordText={this.props.decoratedText}
            contentState={this.props.contentState}
            entityKey={this.props.entityKey}
            onSave={(newText) => {
              const event = new CustomEvent('word-save', { 
                detail: { entityKey: this.props.entityKey, text: newText } 
              });
              window.dispatchEvent(event);
              this.handleEditComplete();
            }}
            onCancel={this.handleEditComplete}
          />
        )}
      </span>
    );
  }
}

Word.propTypes = {
  contentState: PropTypes.object,
  entityKey: PropTypes.string,
  children: PropTypes.array,
  decoratedText: PropTypes.string
};

export default Word;
