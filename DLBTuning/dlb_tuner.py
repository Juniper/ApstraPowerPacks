from power_pack import PowerPackBase


class DLBTunerPack(PowerPackBase):
    def __init__(self):
        super().__init__(worker_callback=self.worker, checker_callback=self.get_pause)
        self.ps_manager = self.setup['management_property_set']
        self.bp_id = self.get_bp_id()
        self.lb_policy = self.get_lb_policy()
        self.oos_packets = 0
        self.old_oos = 0
        self.inactivity_timer_delta = self.get_inactivity_timer_delta()

    def update_dlb_inactivity_interval(self, delta):
        policy = self.aos_client.get_load_balancing_policy(self.bp_id, self.lb_policy)
        inactivity_interval = policy['dlb_options']['flowlet_options']['inactivity_interval']
        print(f"Current Inactivity Interval {inactivity_interval}")
        policy['dlb_options']['flowlet_options']['inactivity_interval'] = inactivity_interval + delta
        self.aos_client.update_load_balancing_policy(self.bp_id, policy['id'], policy)
        self.aos_client.deploy_blueprint(self.bp_id,
            f"OOS Packets seen {self.oos_packets}. Updating inactivity timer to {inactivity_interval + delta}")

    def worker(self):
        # Get pause value
        self.unchanged = 2
        oos = self.aos_client.get_oos_anomalies(self.bp_id)
        oos_packets = 0
        delta = 0
        for o in oos:
            oos_packets = oos_packets + o['actual']['value']

        print(f"Total OOS packets = {oos_packets}")

        if self.old_oos < oos_packets:
            # More OOS packets than before
            print(f"More OOS than before {self.old_oos}<{oos_packets}")
            delta = self.inactivity_timer_delta


        if delta != 0:
            print(f"updating dlb inactivity interval by {delta}")
            self.update_dlb_inactivity_interval(delta)
            self.unchanged = 2
        else:
            print(f"dlb inactivity interval unchanged {self.old_oos} >= {oos_packets}")
            self.unchanged = self.unchanged - 1

        if self.unchanged == 0:
            self.old_oos = 0
            self.unchanged = 2
        else:
            self.old_oos = oos_packets

    def get_pause(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            return ps['values'].get('pause') and str(ps['values'].get('pause')).upper() == "TRUE"
        return False

    def get_bp_id(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            bp = ps['values'].get("blueprint")
            if bp:
                return self.aos_client.get_bp_by_label(bp.strip())['id']
            return ps['values'].get("blueprint_id")
        return self.setup.get('blueprint_id')

    def get_lb_policy(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            return ps['values'].get("lb_policy")
        return self.setup.get('lb_policy')

    def get_inactivity_timer_delta(self):
        ps = self.aos_client.get_property_set(self.ps_manager)
        if ps.get('values'):
            return ps['values'].get("inactivity_timer_delta")
        return self.setup.get('inactivity_timer_delta')


if __name__ == '__main__':
    pp = DLBTunerPack()
    pp.start_threads(blocking=True)
