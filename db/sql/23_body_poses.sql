-- 촬영 자세 정보 (profiles 와 1:1)
CREATE TABLE IF NOT EXISTS body.poses (
  profile_id         INT PRIMARY KEY,
  ref_pose           VARCHAR(10),        -- A / T 기준 자세
  arm_angle_deg      DECIMAL(5,1),
  pelvis_tilt_deg    DECIMAL(5,1),
  shoulder_tilt_deg  DECIMAL(5,1),
  CONSTRAINT chk_poses_ref_pose CHECK (ref_pose IN ('A', 'T')),
  FOREIGN KEY (profile_id) REFERENCES body.profiles(profile_id)
);
