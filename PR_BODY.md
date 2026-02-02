## Summary

Redesigned the TUI with a Firefoo-inspired dark theme for better usability.

## Changes

### Redesigned CSS (`styles.tcss`)
- Firefoo-inspired dark theme with cleaner, minimal design
- Reduced panel heights (3 → 2 lines)
- Added hover effects, focus states, and rounded corners
- Better scrollbar styling with accent color

### New Spinner Widget (`spinner.py`)
- Animated loading spinner for async operations
- Loading overlay component

### Improved Help Screen (`help.py`)
- Better visual hierarchy with reversed key indicators
- Clear section grouping

### Enhanced Document Table (`document_table.py`)
- Loading state indicator
- Better empty states with helpful messages and emojis
- Icons for column headers
- Filter support for documents

### Improved JSON Viewer (`json_viewer.py`)
- Document summary display
- Type-aware value formatting
- Better error handling and empty states

## Testing

Run the TUI to see the changes:
```bash
fayastore tui
```

## Notes
- All changes are backward compatible
- No breaking changes to the API
- Dependencies unchanged
