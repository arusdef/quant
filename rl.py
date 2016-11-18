
# coding: utf-8

# # Reinforcement Learning in Tensorflow Tutorial 2
# ## The Cart-Pole Task
# 
# Parts of this tutorial are based on code by [Andrej Karpathy](https://gist.github.com/karpathy/a4166c7fe253700972fcbc77e4ea32c5) and [korymath](https://gym.openai.com/evaluations/eval_a0aVJrGSyW892vBM04HQA).

import numpy as np 
import cPickle as pickle
import tensorflow as tf
import matplotlib.pyplot as plt
import math
import csv
import sys

# hyperparameters
H = 80 # number of hidden layer neurons
batch_size = 10 # every how many episodes to do a param update?
# batch_size = 50 # every how many episodes to do a param update?
learning_rate = 1e-2 # feel free to play with this to train faster or more stably.
gamma = 1 # discount factor for reward
D = (3 * 2) + (4 * 11) # input dimensionality: 3 economic factor (2 dimens), 4 securities with 11 dimens
exploration_rate = 0.2

# In[5]:

tf.reset_default_graph()

#This defines the network as it goes from taking an observation of the environment to 
#giving a probability of chosing to the action of moving left or right.
observations = tf.placeholder(tf.float32, [None,D] , name="input_x")
W1 = tf.get_variable("W1", shape=[D, H],
           initializer=tf.contrib.layers.xavier_initializer())
layer1 = tf.nn.relu(tf.matmul(observations,W1))
W2 = tf.get_variable("W2", shape=[H, 4], # 4 dimen output for each security
#W2 = tf.get_variable("W2", shape=[H, 3],
           initializer=tf.contrib.layers.xavier_initializer())
score = tf.matmul(layer1,W2)
probability = tf.nn.sigmoid(score)

#From here we define the parts of the network needed for learning a good policy.
tvars = tf.trainable_variables()
input_y = tf.placeholder(tf.float32,[None,4], name="input_y") # Prior output
advantages = tf.placeholder(tf.float32,name="reward_signal")

# The loss function. This sends the weights in the direction of making actions 
# that gave good advantage (reward over time) more likely, and actions that didn't less likely.
loss = -tf.reduce_mean((tf.log(input_y - probability)) * advantages)
newGrads = tf.gradients(loss,tvars)

# Once we have collected a series of gradients from multiple episodes, we apply them.
# We don't just apply gradeients after every episode in order to account for noise in the reward signal.
adam = tf.train.AdamOptimizer(learning_rate=learning_rate) # Our optimizer
W1Grad = tf.placeholder(tf.float32,name="batch_grad1") # Placeholders to send the final gradients through when we update.
W2Grad = tf.placeholder(tf.float32,name="batch_grad2")
batchGrad = [W1Grad,W2Grad]
updateGrads = adam.apply_gradients(zip(batchGrad,tvars))


# ### Advantage function
# This function allows us to weigh the rewards our agent recieves. In the context of the Cart-Pole task, we want actions that kept the pole in the air a long time to have a large reward, and actions that contributed to the pole falling to have a decreased or negative reward. We do this by weighing the rewards from the end of the episode, with actions at the end being seen as negative, since they likely contributed to the pole falling, and the episode ending. Likewise, early actions are seen as more positive, since they weren't responsible for the pole falling.

# In[6]:

def discount_rewards(r):
    """ take 1D float array of rewards and compute discounted reward """
    discounted_r = np.zeros_like(r)
    running_add = 0
    for t in reversed(xrange(0, r.size)):
        running_add = running_add * gamma + r[t]
        discounted_r[t] = running_add
        #discounted_r[t] = r[t]
    return discounted_r


# ### Running the Agent and Environment

# Here we run the neural network agent, and have it act in the CartPole environment.

# In[8]:

xs,hs,dlogps,drs,ys,tfps = [],[],[],[],[],[]
running_reward = None
reward_sum = 0
episode_number = 1
total_episodes = 10000
init = tf.initialize_all_variables()

input_data = list(csv.reader(open("data/market.csv")))
input_index = 1
equity = 1.0  # 1 unit of money, to start

# Launch the graph
with tf.Session() as sess:
    rendering = False
    sess.run(init)

    # TODO no env
    input_index = 1 # Ignore csv header
    equity = 1.0  # 1 unit of money, to start
    observation = input_data[input_index][1:D+1] # Ignore timestamp, don't want that in weights
    observation = np.array(map(float, observation))

    # Reset the gradient placeholder. We will collect gradients in 
    # gradBuffer until we are ready to update our policy network. 
    gradBuffer = sess.run(tvars)
    for ix,grad in enumerate(gradBuffer):
        gradBuffer[ix] = grad * 0
    
    while episode_number <= total_episodes:
        # Make sure the observation is in a shape the network can handle.
        x = np.reshape(observation,[1,D])
        
        # Run the policy network and get an action to take. Normalize output from Neural Net to sum to 1
        portfolio = np.reshape(sess.run(probability,feed_dict={observations: x}), [4])

        # Add random noise to portfolio for exploration
        portfolio = [p + (0.5 * exploration_rate * np.random.uniform() - exploration_rate) for p in portfolio]

        # Normalize portfolio
        port_norm = sum(portfolio)
        portfolio = [p/port_norm for p in portfolio]
        # print portfolio 

        ys.append(portfolio) # portfolio output
        xs.append(x) # observation

        # print
        # print "======================="
        # print "Time Step: %d" % input_index

        # Reward is this day's gains or losses compared to tomorrow, with some penalty for changes in portfolio
        input_index += 1
        observation = input_data[input_index][1:D+1] # Ignore timestamp, don't want that in weights
        observation = np.array(map(float, observation))
        next_spy_change = observation[7]
        next_slv_change = observation[7+11]
        next_gld_change = observation[7+22]
        next_uso_change = observation[7+33]
        #print "SPY: %s" % next_spy_change
        #print "SLV: %s" % next_slv_change
        #print "GLD: %s" % next_gld_change
        #print "USO: %s" % next_uso_change
        #print

        spy_reward = next_spy_change * portfolio[0]
        slv_reward = next_slv_change * portfolio[1]
        gld_reward = next_gld_change * portfolio[2]
        uso_reward = next_uso_change * portfolio[3]
        #print "SPY Reward: %s" % spy_reward
        #print "SLV Reward: %s" % slv_reward
        #print "GLD Reward: %s" % gld_reward
        #print "USO Reward: %s" % uso_reward
        #print

        profit = spy_reward + slv_reward + gld_reward + uso_reward
        reward = profit * equity
        equity = equity * (1 + profit)
        # print "Reward: %s" % reward
        # print "Equity : %s" % equity 
        # print

        done = input_index == 2207 or equity <= 0.1

        # if episode_number > 1 and input_index > 3:
        #     exit()

        # Final reward is portfolio's liquid value
        if done:
            reward = equity
            print "Done Reward: %s" % reward
            print "Equity: %s at time step %d" % (equity, input_index)
            print "Reward Sum: %s" % (reward + reward_sum)
            print

        reward_sum += reward
        drs.append(reward) # record reward (has to be done after we call step() to get reward for previous action)

        if done: 
            episode_number += 1
            # stack together all inputs, hidden states, action gradients, and rewards for this episode
            epx = np.vstack(xs)
            epy = np.vstack(ys)
            epr = np.vstack(drs)
            tfp = tfps
            xs,hs,dlogps,drs,ys,tfps = [],[],[],[],[],[] # reset array memory

            # compute the discounted reward backwards through time
            # print "EPR: %s" % epr
            discounted_epr = discount_rewards(epr) # TODO perhaps figure this out better discount_rewards(epr)
            # print "DISCOUNTED EPR: %s" % discounted_epr
            # size the rewards to be unit normal (helps control the gradient estimator variance)
            discounted_epr -= np.mean(discounted_epr)
            # print "MEAN EPR: %s" % discounted_epr
            discounted_epr /= np.std(discounted_epr)
            #print "STD EPR: %s" % discounted_epr

            
            # Get the gradient for this episode, and save it in the gradBuffer
            tGrad = sess.run(newGrads,feed_dict={observations: epx, input_y: epy, advantages: discounted_epr})
            for ix,grad in enumerate(tGrad):
                gradBuffer[ix] += grad
                
            # If we have completed enough episodes, then update the policy network with our gradients.
            if episode_number % batch_size == 0: 
                sess.run(updateGrads,feed_dict={W1Grad: gradBuffer[0],W2Grad:gradBuffer[1]})
                for ix,grad in enumerate(gradBuffer):
                    gradBuffer[ix] = grad * 0
                
                # Give a summary of how well our network is doing for each batch of episodes.
                running_reward = reward_sum if running_reward is None else running_reward * 0.99 + reward_sum * 0.01
                print 'Average reward for episode %f.  Total average reward %f.' % (reward_sum/batch_size, running_reward/batch_size)
                
                reward_sum = 0
            
            # TODO no env
            input_index = 1 # Ignore csv header
            equity = 1.0  # 1 unit of money, to start
            observation = input_data[input_index][1:D+1] # Ignore timestamp, don't want that in weights
            observation = np.array(map(float, observation))
            
        
print episode_number,'Episodes completed.'

