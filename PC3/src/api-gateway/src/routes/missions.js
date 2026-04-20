/**
 * Mission Routes
 * 
 * POST /api/missions/start
 * POST /api/missions/:id/end
 * GET  /api/missions
 */

'use strict';

const express = require('express');
const missionService = require('../services/missionService');

const router = express.Router();

router.get('/', async (req, res, next) => {
  try {
    const droneId = req.query.droneId;
    const missions = await missionService.getMissions(droneId);
    res.json({ success: true, count: missions.length, data: missions });
  } catch (err) { next(err); }
});

router.post('/start', async (req, res, next) => {
  try {
    const { droneId, waypoints } = req.body;
    const mission = await missionService.startMission(droneId || 'drone_001', waypoints);
    res.status(201).json({ success: true, mission });
  } catch (err) { next(err); }
});

router.post('/:id/end', async (req, res, next) => {
  try {
    const mission = await missionService.endMission(req.params.id, req.body.summary);
    res.json({ success: true, mission });
  } catch (err) { next(err); }
});

module.exports = router;
