/**
 * Command Routes
 *
 * POST /api/commands              - Send a flight command to drone via Kafka
 * GET  /api/commands/types        - List all valid command types
 *
 * Example body:
 *  { "type": "takeoff", "altitude": 20, "drone_id": "drone_001" }
 *  { "type": "goto", "latitude": -1.2921, "longitude": 36.8219, "altitude": 50 }
 *  { "type": "land" }
 *  { "type": "rtl" }
 *  { "type": "arm" }
 *  { "type": "emergency_stop" }
 */

'use strict';

const express = require('express');
const { body, validationResult } = require('express-validator');
const commandService = require('../services/commandService');

const router = express.Router();

// ─── Send command ─────────────────────────────────────────────────────────────
router.post(
  '/',
  [
    body('type').notEmpty().withMessage('Command type is required'),
    body('drone_id').optional().isString(),
    body('altitude').optional().isFloat({ min: 1, max: 120 }),
    body('latitude').optional().isFloat({ min: -90,  max: 90  }),
    body('longitude').optional().isFloat({ min: -180, max: 180 }),
  ],
  async (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    try {
      const result = await commandService.sendCommand(req.body);
      res.status(202).json(result);   // 202 Accepted — command is async
    } catch (err) {
      if (err.message.includes('Unknown command') || err.message.includes('requires field')) {
        return res.status(400).json({ error: err.message });
      }
      next(err);
    }
  }
);

// ─── List valid types ─────────────────────────────────────────────────────────
router.get('/types', (req, res) => {
  res.json({
    success: true,
    commands: commandService.getCommandTypes(),
  });
});

module.exports = router;
