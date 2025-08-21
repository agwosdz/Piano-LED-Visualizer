# Project Requirements and Planning (PRP)
## Enhanced Learn Functionality for Piano LED Visualizer

### Version: 1.0
### Date: December 2024
### Author: AI Assistant

---

## 1. Executive Summary

This document outlines the requirements and planning for enhancing the Piano LED Visualizer's Learn functionality with advanced color customization and a flying notes visualization interface. The project aims to provide users with more granular control over visual feedback during learning sessions and introduce an immersive flying notes display similar to popular piano learning applications.

## 2. Current State Analysis

### 2.1 Existing Learn Functionality
The current system includes:
- Basic MIDI learning with note-on/note-off detection
- Hand detection via MIDI channels (channel 1 = right hand, channel 2 = left hand)
- Simple color palette for left/right hands (`hand_colorList`, `hand_colorR`, `hand_colorL`)
- Future notes preview with dimmed colors
- Wrong notes indication in red
- Practice modes: Melody, Rhythm, Listen
- Web interface with basic controls
- Sheet music synchronization

### 2.2 Current Architecture Components
- **LearnMIDI class** (`lib/learnmidi.py`): Core learning logic
- **ColorMode system** (`lib/color_mode.py`): Color management
- **UserSettings** (`lib/usersettings.py`): Configuration management
- **Web Interface** (`webinterface/`): User controls and visualization
- **MIDI Event Processor** (`lib/midi_event_processor.py`): MIDI handling

### 2.3 Current Limitations
- Limited color customization (only basic hand colors)
- No distinction between white/black key colors
- No separate upcoming note colors
- Static LED-only visualization
- No flying notes interface

## 3. Project Requirements

### 3.1 Feature 1: Enhanced Color Customization

#### 3.1.1 Left/Right Hand White/Black Note Colors
**Requirements:**
- Separate color settings for left hand white keys
- Separate color settings for left hand black keys
- Separate color settings for right hand white keys
- Separate color settings for right hand black keys
- Maintain backward compatibility with existing color system
- Real-time color updates during learning sessions

**Technical Specifications:**
- Extend `hand_colorList` structure or create new settings
- Add note type detection (white vs black keys)
- Modify `light_up_predicted_future_notes()` method
- Update web interface controls

#### 3.1.2 Upcoming Notes Color Customization
**Requirements:**
- Customizable colors for upcoming left hand white keys
- Customizable colors for upcoming left hand black keys
- Customizable colors for upcoming right hand white keys
- Customizable colors for upcoming right hand black keys
- Adjustable brightness/opacity for upcoming notes
- Independent control from current note colors

### 3.2 Feature 2: Flying Notes Visualization Interface

#### 3.2.1 Core Visualization Requirements
**Requirements:**
- Web-based flying notes display similar to flyingnotes.app
- Notes fly downward (opposite to flyingnotes.app)
- Real-time synchronization with MIDI playback
- Visual representation of piano keyboard at bottom
- Smooth animation with configurable speed
- Responsive design for various screen sizes

#### 3.2.2 Visual Elements
**Requirements:**
- Piano keyboard visualization at bottom of screen
- Flying note blocks with hand-specific colors
- Note duration representation (block length)
- Velocity representation (block opacity/size)
- Hand separation (left/right visual distinction)
- White/black key visual distinction
- Timing grid/measures display

#### 3.2.3 Integration Requirements
**Requirements:**
- Seamless integration with existing learn functionality
- Synchronization with LED strip feedback
- Compatible with all practice modes (Melody, Rhythm, Listen)
- Real-time updates during learning sessions
- Performance optimization for smooth animation

## 4. Technical Architecture Design

### 4.1 Database/Settings Schema Changes

#### 4.1.1 New Settings Structure
```xml
<!-- Enhanced Learn Color Settings -->
<learn_colors>
    <left_hand>
        <white_keys>
            <current>[0, 255, 0]</current>
            <upcoming>[0, 128, 0]</upcoming>
        </white_keys>
        <black_keys>
            <current>[0, 200, 0]</current>
            <upcoming>[0, 100, 0]</upcoming>
        </black_keys>
    </left_hand>
    <right_hand>
        <white_keys>
            <current>[0, 0, 255]</current>
            <upcoming>[0, 0, 128]</upcoming>
        </white_keys>
        <black_keys>
            <current>[0, 0, 200]</current>
            <upcoming>[0, 0, 100]</upcoming>
        </black_keys>
    </right_hand>
</learn_colors>

<!-- Flying Notes Settings -->
<flying_notes>
    <enabled>0</enabled>
    <speed>1.0</speed>
    <note_height>20</note_height>
    <keyboard_height>80</keyboard_height>
    <show_measures>1</show_measures>
    <animation_smoothness>60</animation_smoothness>
</flying_notes>
```

### 4.2 Component Modifications

#### 4.2.1 LearnMIDI Class Enhancements
**File:** `lib/learnmidi.py`

**New Methods:**
```python
def get_note_type(self, note):
    """Determine if note is white or black key"""
    
def get_learn_color(self, hand, note_type, is_upcoming=False):
    """Get color based on hand, note type, and timing"""
    
def light_up_enhanced_notes(self, notes, is_upcoming=False):
    """Enhanced note lighting with new color system"""
```

**Modified Methods:**
- `light_up_predicted_future_notes()`: Use new color system
- `handle_wrong_notes()`: Support enhanced colors
- `learn_midi()`: Integration with flying notes

#### 4.2.2 New FlyingNotesRenderer Class
**File:** `lib/flying_notes_renderer.py`

```python
class FlyingNotesRenderer:
    def __init__(self, usersettings, learnmidi):
        # Initialize WebSocket connection
        # Set up animation parameters
        
    def render_frame(self, current_time, notes_data):
        # Calculate note positions
        # Generate frame data for web interface
        
    def get_notes_in_timeframe(self, start_time, end_time):
        # Extract notes for current view window
        
    def calculate_note_position(self, note, timing):
        # Calculate X,Y position for flying note
```

#### 4.2.3 Web Interface Enhancements

**New Files:**
- `webinterface/static/js/flying_notes.js`: Flying notes animation engine
- `webinterface/static/css/flying_notes.css`: Styling for flying notes
- `webinterface/templates/flying_notes.html`: Flying notes display

**Modified Files:**
- `webinterface/templates/songs.html`: Add flying notes toggle and controls
- `webinterface/views_api.py`: Add flying notes data endpoints
- `webinterface/static/js/index.js`: Integration with existing controls

### 4.3 API Endpoints

#### 4.3.1 New REST Endpoints
```python
@webinterface.route('/api/flying_notes/data')
def get_flying_notes_data():
    # Return current notes data for animation
    
@webinterface.route('/api/learn_colors/update', methods=['POST'])
def update_learn_colors():
    # Update enhanced color settings
    
@webinterface.route('/api/flying_notes/settings', methods=['GET', 'POST'])
def flying_notes_settings():
    # Get/set flying notes configuration
```

#### 4.3.2 WebSocket Integration
```python
class FlyingNotesWebSocket:
    def __init__(self):
        # Real-time data streaming for smooth animation
        
    def broadcast_notes_update(self, notes_data):
        # Send real-time updates to connected clients
```

## 5. Implementation Plan

### 5.1 Phase 1: Enhanced Color System (Weeks 1-2)

#### Week 1: Backend Implementation
- [ ] Extend UserSettings for new color structure
- [ ] Add note type detection (white/black keys)
- [ ] Modify LearnMIDI class for enhanced colors
- [ ] Update default_settings.xml
- [ ] Create migration script for existing settings

#### Week 2: Frontend Integration
- [ ] Design color picker UI components
- [ ] Update songs.html with new color controls
- [ ] Add API endpoints for color management
- [ ] Implement real-time color preview
- [ ] Testing and bug fixes

### 5.2 Phase 2: Flying Notes Foundation (Weeks 3-4)

#### Week 3: Core Animation Engine
- [ ] Create FlyingNotesRenderer class
- [ ] Implement basic note positioning algorithms
- [ ] Set up WebSocket infrastructure
- [ ] Create basic HTML5 Canvas rendering
- [ ] Piano keyboard visualization

#### Week 4: MIDI Integration
- [ ] Synchronize with LearnMIDI timing
- [ ] Implement note data extraction
- [ ] Add real-time note streaming
- [ ] Basic animation testing
- [ ] Performance optimization

### 5.3 Phase 3: Advanced Flying Notes (Weeks 5-6)

#### Week 5: Visual Enhancements
- [ ] Hand-specific note coloring
- [ ] Velocity-based visual effects
- [ ] Note duration representation
- [ ] Measure lines and timing grid
- [ ] Smooth animation interpolation

#### Week 6: UI Integration
- [ ] Flying notes toggle in web interface
- [ ] Settings panel for flying notes
- [ ] Responsive design implementation
- [ ] Integration with existing practice modes
- [ ] Cross-browser compatibility testing

### 5.4 Phase 4: Testing and Polish (Week 7)

- [ ] Comprehensive testing across all features
- [ ] Performance optimization
- [ ] User experience refinements
- [ ] Documentation updates
- [ ] Bug fixes and edge case handling

## 6. Technical Specifications

### 6.1 Performance Requirements
- Flying notes animation: 60 FPS minimum
- Real-time latency: <50ms for note updates
- Memory usage: <100MB additional for flying notes
- CPU usage: <10% additional overhead

### 6.2 Browser Compatibility
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (responsive design)

### 6.3 Hardware Requirements
- Raspberry Pi 3B+ or higher for optimal performance
- Minimum 1GB RAM
- Hardware acceleration support preferred

## 7. User Interface Design

### 7.1 Enhanced Color Controls
```
┌─ Learn Color Settings ─────────────────────┐
│                                            │
│ Left Hand:                                 │
│   White Keys: [Current] [●] [Upcoming] [●] │
│   Black Keys: [Current] [●] [Upcoming] [●] │
│                                            │
│ Right Hand:                                │
│   White Keys: [Current] [●] [Upcoming] [●] │
│   Black Keys: [Current] [●] [Upcoming] [●] │
│                                            │
│ [Reset to Defaults] [Apply]                │
└────────────────────────────────────────────┘
```

### 7.2 Flying Notes Interface
```
┌─ Flying Notes Display ─────────────────────┐
│                                            │
│           ♪ ♫ ♪                           │
│         ♪     ♫                           │
│       ♪         ♪                         │
│     ♫             ♫                       │
│   ♪                 ♪                     │
│ ♫                     ♫                   │
│                                            │
│ ████████████████████████████████████████   │
│ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██ ██   │ (Piano)
│ ████████████████████████████████████████   │
│                                            │
│ [●] Enable  Speed: [====|====]  [Settings] │
└────────────────────────────────────────────┘
```

## 8. Testing Strategy

### 8.1 Unit Testing
- Color system functionality
- Note type detection accuracy
- Flying notes positioning algorithms
- WebSocket communication
- Settings persistence

### 8.2 Integration Testing
- MIDI synchronization accuracy
- Real-time performance under load
- Cross-component communication
- Web interface responsiveness
- LED strip integration

### 8.3 User Acceptance Testing
- Learning experience improvement
- Visual clarity and usability
- Performance on target hardware
- Accessibility considerations
- Mobile device compatibility

## 9. Risk Assessment

### 9.1 Technical Risks
- **Performance Impact**: Flying notes may affect system performance
  - *Mitigation*: Optimize rendering, implement frame rate limiting
- **Browser Compatibility**: Advanced animations may not work on older browsers
  - *Mitigation*: Graceful degradation, feature detection
- **Timing Synchronization**: Complex timing between MIDI, LEDs, and flying notes
  - *Mitigation*: Centralized timing system, extensive testing

### 9.2 User Experience Risks
- **Complexity Overload**: Too many options may confuse users
  - *Mitigation*: Progressive disclosure, sensible defaults
- **Visual Distraction**: Flying notes may distract from actual playing
  - *Mitigation*: Customizable opacity, disable option

## 10. Success Metrics

### 10.1 Technical Metrics
- Animation frame rate: >55 FPS average
- Note timing accuracy: <20ms deviation
- Memory usage increase: <15%
- Load time impact: <2 seconds additional

### 10.2 User Experience Metrics
- Feature adoption rate: >60% of users try flying notes
- Color customization usage: >40% modify default colors
- Performance satisfaction: >85% report smooth operation
- Learning effectiveness: Subjective improvement reports

## 11. Future Enhancements

### 11.1 Potential Extensions
- 3D flying notes visualization
- Custom note shapes and effects
- Advanced timing visualization (swing, rubato)
- Multi-track visual separation
- Export flying notes as video
- VR/AR integration possibilities

### 11.2 Integration Opportunities
- External software compatibility (Synthesia, etc.)
- MIDI file format extensions
- Cloud-based settings synchronization
- Social features (sharing visualizations)

## 12. Conclusion

This PRP outlines a comprehensive enhancement to the Piano LED Visualizer's Learn functionality. The implementation will significantly improve the learning experience through enhanced visual feedback and modern interface design while maintaining the system's core reliability and performance.

The phased approach ensures manageable development cycles with clear milestones and testing points. The modular design allows for independent development and testing of each feature while maintaining system integration.

---

**Document Status**: Draft v1.0  
**Next Review**: Upon development team approval  
**Estimated Completion**: 7 weeks from project start  
**Priority**: High - User Experience Enhancement