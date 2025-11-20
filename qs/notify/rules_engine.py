from __future__ import annotations

from typing import Dict, List, Callable, Optional
from datetime import datetime
from ..utils.logger import get_logger
from ..notify.twilio_client import send_sms_update

logger = get_logger(__name__)


class AlertRule:
    """Alert rule definition."""
    
    def __init__(
        self,
        name: str,
        condition: Callable,
        message_template: str,
        priority: str = "normal",
        enabled: bool = True
    ):
        self.name = name
        self.condition = condition
        self.message_template = message_template
        self.priority = priority  # "low", "normal", "high", "critical"
        self.enabled = enabled
        self.last_triggered: Optional[datetime] = None
        self.trigger_count = 0
    
    def check(self, context: Dict) -> Optional[str]:
        """Check if rule should trigger."""
        if not self.enabled:
            return None
        
        try:
            if self.condition(context):
                self.last_triggered = datetime.now()
                self.trigger_count += 1
                return self.message_template.format(**context)
        except Exception as e:
            logger.error(f"Error checking rule {self.name}: {e}")
        
        return None


class AlertRulesEngine:
    """
    Rules engine for SMS alerts.
    """
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules."""
        # Drawdown alert
        self.add_rule(AlertRule(
            name="high_drawdown",
            condition=lambda ctx: ctx.get('drawdown_pct', 0) > 5.0,
            message_template="⚠️ High Drawdown Alert\nDrawdown: {drawdown_pct:.2f}%\nCurrent Equity: ${current_equity:,.2f}",
            priority="high"
        ))
        
        # Daily loss alert
        self.add_rule(AlertRule(
            name="daily_loss_limit",
            condition=lambda ctx: ctx.get('daily_loss_pct', 0) > 3.0,
            message_template="⚠️ Daily Loss Alert\nDaily Loss: {daily_loss_pct:.2f}%\nPnL: ${daily_pnl:,.2f}",
            priority="high"
        ))
        
        # Circuit breaker alert
        self.add_rule(AlertRule(
            name="circuit_breaker",
            condition=lambda ctx: ctx.get('circuit_breaker_active', False),
            message_template="🚨 CIRCUIT BREAKER TRIGGERED\nReason: {circuit_breaker_reason}\nAll trading halted.",
            priority="critical"
        ))
        
        # Large position alert
        self.add_rule(AlertRule(
            name="large_position",
            condition=lambda ctx: ctx.get('position_pct', 0) > 15.0,
            message_template="⚠️ Large Position Alert\n{symbol}: {position_pct:.1f}% of portfolio\nValue: ${position_value:,.2f}",
            priority="normal"
        ))
        
        # Data quality alert
        self.add_rule(AlertRule(
            name="data_quality",
            condition=lambda ctx: ctx.get('data_quality_issues', 0) > 10,
            message_template="⚠️ Data Quality Alert\n{data_quality_issues} issues detected\nCheck data quality monitor.",
            priority="normal"
        ))
        
        # Execution quality alert
        self.add_rule(AlertRule(
            name="high_slippage",
            condition=lambda ctx: ctx.get('avg_slippage_bps', 0) > 50,
            message_template="⚠️ High Slippage Alert\nAvg Slippage: {avg_slippage_bps:.1f} bps\nConsider adjusting execution strategy.",
            priority="normal"
        ))
    
    def add_rule(self, rule: AlertRule):
        """Add a custom alert rule."""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed alert rule: {rule_name}")
    
    def enable_rule(self, rule_name: str):
        """Enable an alert rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Enabled rule: {rule_name}")
    
    def disable_rule(self, rule_name: str):
        """Disable an alert rule."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Disabled rule: {rule_name}")
    
    def check_all(self, context: Dict) -> List[str]:
        """Check all rules and return triggered alerts."""
        alerts = []
        
        for rule in self.rules:
            message = rule.check(context)
            if message:
                alerts.append({
                    'rule': rule.name,
                    'message': message,
                    'priority': rule.priority
                })
        
        return alerts
    
    def send_alerts(self, context: Dict, send_sms: bool = True) -> int:
        """Check rules and send SMS alerts."""
        alerts = self.check_all(context)
        
        if not alerts:
            return 0
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        alerts.sort(key=lambda x: priority_order.get(x['priority'], 99))
        
        sent_count = 0
        for alert in alerts:
            if send_sms:
                success = send_sms_update(alert['message'])
                if success:
                    sent_count += 1
                    logger.info(f"Sent alert: {alert['rule']} ({alert['priority']})")
            else:
                logger.info(f"Alert would be sent: {alert['rule']} - {alert['message']}")
                sent_count += 1
        
        return sent_count
    
    def get_rule_stats(self) -> Dict:
        """Get statistics about rule triggers."""
        return {
            rule.name: {
                'enabled': rule.enabled,
                'trigger_count': rule.trigger_count,
                'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None
            }
            for rule in self.rules
        }


# Global rules engine
_rules_engine: Optional[AlertRulesEngine] = None


def get_rules_engine() -> AlertRulesEngine:
    """Get global alert rules engine."""
    global _rules_engine
    if _rules_engine is None:
        _rules_engine = AlertRulesEngine()
    return _rules_engine

