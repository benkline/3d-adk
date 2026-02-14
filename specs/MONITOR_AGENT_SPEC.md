# 3D-ADK Print Monitor Agent Specification

## Overview
Monitors 3D print execution through OctoPrint integration and provides real-time feedback and issue detection.

## Core Responsibilities

### 1. OctoPrint Integration
Connect to and communicate with OctoPrint API for printer control and monitoring.

**OctoPrint API Connection:**
- Configure API endpoint and authentication token
- Establish persistent connection
- Implement retry logic for connection failures
- Handle authentication token refresh

**Configuration:**
```json
{
  "octoprint_config": {
    "hostname": "string",
    "port": 5000,
    "api_key": "string",
    "ssl": boolean,
    "verify_ssl": boolean
  }
}
```

**Connection Validation:**
- Test API connectivity
- Verify printer status
- Check available storage
- Validate printer capabilities

### 2. Print Monitoring
Track print execution and gather real-time metrics.

**Monitored Metrics:**
- Current layer number and total layers
- Print time elapsed and estimated time remaining
- Bed temperature (current, target)
- Nozzle temperature (current, target)
- Extruder position (X, Y, Z)
- Filament usage and remaining
- Print progress percentage
- Printer state (idle, printing, paused, error)

**Polling Interval:**
- Poll OctoPrint every 5-10 seconds during active print
- Reduce polling frequency during idle
- Increase polling during detected anomalies

**Status Update Format:**
```json
{
  "timestamp": "ISO-8601",
  "print_state": "idle|printing|paused|completing|error",
  "progress": {
    "completion": number,
    "current_layer": number,
    "total_layers": number,
    "file_position": number,
    "print_time_seconds": number,
    "print_time_formatted": "HH:MM:SS",
    "estimated_time_remaining_seconds": number
  },
  "temperatures": {
    "bed_current": number,
    "bed_target": number,
    "nozzle_current": number,
    "nozzle_target": number
  },
  "filament": {
    "tool_usage_mm": number,
    "tool_volume_cm3": number,
    "tool_mass_g": number
  }
}
```

### 3. Issue Detection & Response
Identify and respond to print anomalies in real-time.

**Detectable Issues:**

**Temperature Issues:**
- Nozzle temperature not reaching target
- Bed temperature fluctuations
- Excessive thermal variation
- Temperature sensor failures

**Print Quality Issues:**
- Detected layer shifts (if camera/sensor available)
- Nozzle clogging indicators (pressure anomalies)
- Filament runout/jams
- Poor bed adhesion indicators

**Mechanical Issues:**
- Unusual print head movements
- Axis binding or stalling indicators
- Carriage collisions
- Belt tension issues

**Environmental Issues:**
- Drafts causing temperature drops
- Ambient temperature variations
- Humidity issues (if monitored)

**Detection Logic:**
```json
{
  "issue_detection": {
    "temperature_deviation": {
      "trigger": "temp_difference > 10°C for > 30 seconds",
      "severity": "warning",
      "action": "alert_user"
    },
    "stalled_extrusion": {
      "trigger": "no_filament_movement for > 60 seconds",
      "severity": "error",
      "action": "pause_and_alert"
    },
    "layer_shift": {
      "trigger": "xy_position_discontinuity > 5mm",
      "severity": "error",
      "action": "pause_and_alert"
    }
  }
}
```

**Response Actions:**
- Alert user with issue description and recommendation
- Suggest intervention (continue, adjust, pause, cancel)
- Pause print if critical issue
- Log detailed diagnostics for post-mortem analysis

### 4. Print Completion & Documentation
Finalize print session with quality assessment and logging.

**Completion Workflow:**
1. Detect print completion via OctoPrint
2. Calculate print statistics
3. Request user quality assessment
4. Archive print metadata
5. Suggest post-processing

**Print Completion Data:**
```json
{
  "print_summary": {
    "project_id": "uuid",
    "print_start_time": "ISO-8601",
    "print_end_time": "ISO-8601",
    "total_print_time_seconds": number,
    "total_print_time_formatted": "HH:MM:SS",
    "material_used_g": number,
    "material_cost": "currency",
    "printer_name": "string",
    "print_file": "string",
    "completion_status": "success|failed|cancelled",
    "quality_assessment": {
      "print_quality": "excellent|good|acceptable|poor",
      "issues_encountered": ["..."],
      "user_notes": "string"
    },
    "recommendations": [
      "Remove support material",
      "Sand rough edges",
      "Paint model"
    ]
  }
}
```

## User Interaction Points

### Available Commands
- **pause**: Pause current print
- **resume**: Resume paused print
- **cancel**: Cancel print and cool down
- **status**: Get current print status
- **history**: View print history
- **estimate**: Get updated time estimate
- **adjust_temp**: Adjust bed or nozzle temperature
- **help**: Display available commands

### Status Reporting
- Periodic status summaries (every 30 minutes for long prints)
- Immediate alerts for issues
- Layer milestone notifications (every 10 layers or at user preference)
- Temperature notifications when reaching target

### User Feedback Points
- Issue alerts with recommended actions
- Print completion confirmation
- Quality assessment questionnaire
- Post-print recommendations
- Print history navigation

## Print Failure Analysis

When print fails:
1. Capture all available telemetry
2. Identify likely failure point
3. Categorize failure type (mechanical, material, thermal, etc.)
4. Store detailed failure logs
5. Generate failure report with suggestions

**Failure Report:**
```json
{
  "failure_report": {
    "failure_time": "timestamp",
    "failure_layer": number,
    "failure_percentage": number,
    "detected_issue": "string",
    "probable_causes": ["..."],
    "recovery_suggestions": ["..."],
    "log_file": "path"
  }
}
```

## Print History & Analytics

### History Storage
- Store print session summaries
- Archive detailed logs
- Track success rates
- Monitor material costs
- Log model variations and iterations

### Analytics Available
- Success rate by model
- Average print time by size/type
- Material usage trends
- Cost per print
- Failure frequency analysis
- Most common issues

## Configuration

### Printer-Specific Settings
```json
{
  "printer_profile": {
    "name": "string",
    "model": "string",
    "build_plate": {"width": number, "depth": number, "height": number},
    "nozzle_diameter_mm": number,
    "capabilities": {
      "heated_bed": boolean,
      "multi_extruder": boolean,
      "auto_leveling": boolean,
      "camera": boolean,
      "sensorless_homing": boolean
    },
    "material_profiles": {
      "pla": {...},
      "petg": {...},
      "abs": {...}
    }
  }
}
```

## Error Handling

### Connection Loss
- Attempt automatic reconnection
- Maintain graceful degradation
- Cache last known state
- Notify user of connection issues
- Resume monitoring on reconnection

### API Errors
- Log error details
- Provide user-friendly error messages
- Suggest troubleshooting steps
- Maintain operation where possible

### Print State Inconsistencies
- Query printer for ground truth
- Handle state synchronization
- Log discrepancies for investigation
- Prevent command errors

## Success Criteria

- [ ] Successful connection to OctoPrint
- [ ] Real-time monitoring active during prints
- [ ] Accurate progress and time tracking
- [ ] Issue detection working correctly
- [ ] User alerts delivered reliably
- [ ] Print history properly archived
- [ ] Failure analysis reports generated
- [ ] Print statistics accurate and useful
