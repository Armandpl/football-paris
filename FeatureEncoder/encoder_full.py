import numpy as np

class FeatureEncoder:
    def __init__(self):
        self.active = -1
        self.player_pos_x, self.player_pos_y  = 0, 0
        
    def get_feature_dims(self):
        dims = {
            'player':30,
            'ball':18,
            'left_team':10,
            'left_team_closest':10,
            'right_team':10,
            'right_team_closest':10,
        }
        return dims

    def encode(self, obs):
        player_num = obs['active']
        
        player_pos_x, player_pos_y = obs['left_team'][player_num]
        player_direction = obs['left_team_direction'][player_num]
        player_speed = np.linalg.norm(player_direction)
        player_role = obs['left_team_roles'][player_num]
        player_role_onehot = self._encode_role_onehot(player_role)
        player_tired = obs['left_team_tired_factor'][player_num]
        player_yellow_card = obs['left_team_yellow_card'][player_num]
        player_active = obs['left_team_active'][player_num]
        is_dribbling = obs['sticky_actions'][9]
        is_sprinting = obs['sticky_actions'][8]

        ball_x, ball_y, ball_z = obs['ball']
        ball_x_relative = ball_x - player_pos_x
        ball_y_relative = ball_y - player_pos_y
        ball_z_relative = ball_z - 0.0
        ball_direction = obs['ball_direction']
        ball_speed = np.linalg.norm(ball_direction)
        ball_distance = np.linalg.norm([ball_x_relative, ball_y_relative])
        ball_owned = 0.0 
        if obs['ball_owned_team'] == -1:
            ball_owned = 0.0
        else:
            ball_owned = 1.0
        ball_owned_by_us = 0.0
        if obs['ball_owned_team'] == 0:
            ball_owned_by_us = 1.0
        elif obs['ball_owned_team'] == 1:
            ball_owned_by_us = 0.0
        else:
            ball_owned_by_us = 0.0

        avail = self._get_avail(obs, ball_distance)
        player_state = np.concatenate((avail[2:], 
                                       obs['left_team'][player_num], 
                                       player_direction * 100, 
                                       player_role_onehot, 
                                       [player_speed * 100, player_tired, player_yellow_card, player_active, is_dribbling, is_sprinting]))

        ball_which_zone = self._encode_ball_which_zone(ball_x, ball_y) 
        ball_state = np.concatenate((obs['ball'], 
                                     np.array(ball_which_zone),
                                     np.array([ball_x_relative, ball_y_relative, ball_z_relative]),
                                     ball_direction * 20,
                                     np.array([ball_speed * 20, ball_owned, ball_owned_by_us])))
    
        obs_left_team = np.delete(obs['left_team'], player_num, axis=0)
        obs_left_team_direction = np.delete(obs['left_team_direction'], player_num, axis=0)
        obs_left_team_tired_factor = np.delete(obs['left_team_tired_factor'], player_num, axis=0).reshape(-1,1)
        obs_left_team_yellow_card = np.delete(obs['left_team_yellow_card'], player_num, axis=0).reshape(-1,1)
        obs_left_team_active = np.delete(np.float32(obs['left_team_active']), player_num, axis=0).reshape(-1,1)
#         left_team_relative = obs_left_team - obs['left_team'][player_num]
        left_team_relative = obs_left_team
#         left_team_distance = np.linalg.norm(left_team_relative, axis=1, keepdims=True)
        left_team_distance = np.linalg.norm(left_team_relative - obs['left_team'][player_num], axis=1, keepdims=True)
        left_team_speed = np.linalg.norm(obs_left_team_direction, axis=1, keepdims=True)
        left_team_inner_product = np.sum(left_team_relative*obs_left_team_direction, axis=1, keepdims=True)
        left_team_cos = 0 * left_team_inner_product/(left_team_distance*(left_team_speed+1e-8))
        left_team_state = np.concatenate((left_team_relative * 2, 
                                          obs_left_team_direction * 100, 
                                          obs_left_team_tired_factor, 
                                          obs_left_team_yellow_card, 
                                          obs_left_team_active, 
                                          left_team_speed * 100, 
                                          left_team_distance * 2, 
                                          left_team_cos), axis=1)
        left_closest_idx = np.argmin(left_team_distance)
        left_closest_state = left_team_state[left_closest_idx]
        
        
#         right_team_relative = obs_right_team - obs['left_team'][player_num]
        obs_right_team = obs['right_team']
        right_team_relative = obs_right_team
#         right_team_distance = np.linalg.norm(right_team_relative, axis=1, keepdims=True)
        obs_right_team_direction = obs['right_team_direction']
        right_team_tired_factor = obs['right_team_tired_factor'].reshape(-1,1)
        right_team_yellow_card = obs['right_team_yellow_card'].reshape(-1,1)
        right_team_active = obs['right_team_active'].reshape(-1,1)
        right_team_distance = np.linalg.norm(right_team_relative - obs['left_team'][player_num], axis=1, keepdims=True)
        right_team_speed = np.linalg.norm(obs_right_team_direction, axis=1, keepdims=True)
        right_team_inner_product = np.sum(right_team_relative*obs_right_team_direction, axis=1, keepdims=True)
        right_team_cos = 0 * right_team_inner_product/(right_team_distance*(right_team_speed+1e-8))
        right_team_state = np.concatenate((right_team_relative * 2, 
                                           obs_right_team_direction * 100,
                                           right_team_tired_factor,
                                           right_team_yellow_card,
                                           right_team_active,
                                           right_team_speed * 100, 
                                           right_team_distance * 2, 
                                           right_team_cos), axis=1)
        right_closest_idx = np.argmin(right_team_distance)
        right_closest_state = right_team_state[right_closest_idx]
        
        state_dict = {"player": player_state,
                      "ball": ball_state,
                      "left_team" : left_team_state,
                      "left_closest" : left_closest_state,
                      "right_team" : right_team_state,
                      "right_closest" : right_closest_state,
                      "avail" : avail}

        return state_dict
    
    def _get_avail(self, obs, ball_distance):
        avail = [1,1,1,1,1,1,1,1,1,1,1,1]
        NO_OP, MOVE, LONG_PASS, HIGH_PASS, SHORT_PASS, SHOT, SPRINT, RELEASE_MOVE, \
                                                      RELEASE_SPRINT, SLIDE, DRIBBLE, RELEASE_DRIBBLE = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        
        # When opponents owning ball ...
        if obs['ball_owned_team'] == 1: # opponents owning ball
            avail[LONG_PASS], avail[HIGH_PASS], avail[SHORT_PASS], avail[SHOT], avail[DRIBBLE] = 0, 0, 0, 0, 0
        elif obs['ball_owned_team'] == -1 and ball_distance > 0.03 and obs['game_mode'] == 0: # GR ball  and far from me
            avail[LONG_PASS], avail[HIGH_PASS], avail[SHORT_PASS], avail[SHOT], avail[DRIBBLE] = 0, 0, 0, 0, 0
        else:
            avail[SLIDE] = 0
            
        # Dealing with sticky actions
        sticky_actions = obs['sticky_actions']
        if sticky_actions[8] == 0:  # sprinting
            avail[RELEASE_SPRINT] = 0
            
        if sticky_actions[9] == 1:  # dribbling
            avail[SLIDE] = 0
        else:
            avail[RELEASE_DRIBBLE] = 0
            
        if np.sum(sticky_actions[:8]) == 0:
            avail[RELEASE_MOVE] = 0
            
        
        # if too far, no shot
        ball_x, ball_y, _ = obs['ball']
        if ball_x < 0.64 or ball_y < -0.27 or 0.27 < ball_y:
            avail[SHOT] = 0
        elif (0.64 <= ball_x and ball_x<=1.0) and (-0.27<=ball_y and ball_y<=0.27):
            avail[HIGH_PASS], avail[LONG_PASS] = 0, 0
            
            
        if obs['game_mode'] == 2 and ball_x < -0.7:  # Our GoalKick 
            avail = [1,0,0,0,0,0,0,0,0,0,0,0]
            avail[LONG_PASS], avail[HIGH_PASS], avail[SHORT_PASS] = 1, 1, 1
            return np.array(avail)
        
        elif obs['game_mode'] == 4 and ball_x > 0.9:  # Our CornerKick
            avail = [1,0,0,0,0,0,0,0,0,0,0,0]
            avail[LONG_PASS], avail[HIGH_PASS], avail[SHORT_PASS] = 1, 1, 1
            return np.array(avail)
        
        elif obs['game_mode'] == 6 and ball_x > 0.6:  # Our PenaltyKick
            avail = [1,0,0,0,0,0,0,0,0,0,0,0]
            avail[SHOT] = 1
            return np.array(avail)
        
        
#         if obs['ball_owned_team'] == 0:  # our team 
#             if obs['game_mode'] == 2:  # GoalKick
#                 avail[SPRINT], avail[DRIBBLE] = 0, 0
#             elif obs['game_mode'] == 3:  # FreeKick
#                 avail[DRIBBLE] = 0
#             elif obs['game_mode'] == 4:  # Corner
#                 avail[SHOT], avail[SPRINT], avail[DRIBBLE] = 0, 0, 0
#             elif obs['game_mode'] == 5:  #ThrowIn
#                 avail[SHOT], avail[SPRINT], avail[DRIBBLE] = 0, 0, 0
#             elif obs['game_mode'] == 6:  # Penalty
#                 avail[LONG_PASS], avail[HIGH_PASS], avail[SHORT_PASS], avail[DRIBBLE] = 0, 0, 0, 0
            
        return np.array(avail)
        
    def _encode_ball_which_zone(self, ball_x, ball_y):
        MIDDLE_X, PENALTY_X, END_X = 0.2, 0.64, 1.0
        PENALTY_Y, END_Y = 0.27, 0.42
        if   (-END_X <= ball_x    and ball_x < -PENALTY_X)and (-PENALTY_Y < ball_y and ball_y < PENALTY_Y):
            return [1.0,0,0,0,0,0]
        elif (-END_X <= ball_x    and ball_x < -MIDDLE_X) and (-END_Y < ball_y     and ball_y < END_Y):
            return [0,1.0,0,0,0,0]
        elif (-MIDDLE_X <= ball_x and ball_x <= MIDDLE_X) and (-END_Y < ball_y     and ball_y < END_Y):
            return [0,0,1.0,0,0,0]
        elif (PENALTY_X < ball_x  and ball_x <=END_X)     and (-PENALTY_Y < ball_y and ball_y < PENALTY_Y):
            return [0,0,0,1.0,0,0]
        elif (MIDDLE_X < ball_x   and ball_x <=END_X)     and (-END_Y < ball_y     and ball_y < END_Y):
            return [0,0,0,0,1.0,0]
        else:
            return [0,0,0,0,0,1.0]
        

    def _encode_role_onehot(self, role_num):
        result = [0,0,0,0,0,0,0,0,0,0]
        result[role_num] = 1.0
        return np.array(result)