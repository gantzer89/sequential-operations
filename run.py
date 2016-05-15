import argparse
import cPickle as pickle  
import numpy as np
import tensorflow as tf
from tensorflow.models.rnn import rnn, rnn_cell
from seqops.data import generate_sequence
from seqops.data import load_data
from seqops.learner import RecurrentNeuralLearner
from seqops.trainer import AgentTrainer

## In[0]: Parse arguments

parser = argparse.ArgumentParser()
parser.add_argument("train_images_file", help="training images file in NumPy standard binary file format")
parser.add_argument("train_labels_file", help="training labels file in NumPy standard binary file format")
parser.add_argument("convnet_file", help="convolutional network file in packing list file format")
parser.add_argument("learning_rate", help="learning rate", type=float)
parser.add_argument("batch_size", help="batch size", type=int)
parser.add_argument("n_input", help="output of the convnet and input to the RNN", type=int)
parser.add_argument("n_hidden", help="number of features in the hidden layer", type=int)
parser.add_argument("n_first_digit_length", help="length of the first operand", type=int)
parser.add_argument("n_second_digit_length", help="length of the second operand", type=int)
parser.add_argument("training_iters", help="number of training iterations", type=int)
parser.add_argument("display_step", help="how often must be shown training results", type=int)
parser.add_argument("test_images_file", help="testing images file in NumPy standard binary file format")
parser.add_argument("test_labels_file", help="testing labels file in NumPy standard binary file format")
args = parser.parse_args()

## In[1]: Load training data

train_images_file = args.train_images_file
train_labels_file = args.train_labels_file

print "- Loading training data"

digits, digit_labels, symbols, symbol_labels = load_data(train_images_file, train_labels_file)

print "  Finished"

sequence, result, operands = generate_sequence(digits, digit_labels, symbols, symbol_labels,  20, 1, 1)

print "- Size of sequence tensor:", sequence.shape

## In[2]: Create agent

convnet_file = args.convnet_file
learning_rate = args.learning_rate
batch_size = args.batch_size
n_input = args.n_input
n_hidden = args.n_hidden
n_first_digit_length = args.n_first_digit_length
n_second_digit_length = args.n_second_digit_length
n_steps = n_first_digit_length + 1 + n_second_digit_length

assert(n_steps >= 3)
assert(n_steps <= 11)

print "- Creating agent"

'''
agent = RecurrentNeuralLearner(convnet_file, learning_rate, batch_size, n_input, n_hidden, n_steps)
agent.createNetwork()
'''

def buildWeightVariable(shape, init=None):
    """
    Builds the weights variable for the convolutional network.
    """
    if init is None:
        # Builds a variable from a random sequence of given shape with mean 0.0 standard deviation 0.1
        initial = tf.truncated_normal(shape, stddev=0.1)
        return tf.Variable(initial)
    else:
        # Builds a variable from a given tensor
        return tf.Variable(init)

def buildBiasVariable(shape, init=None):
    """
    Builds the bias variable for the convolutional network.
    """
    if init is None:
        # Builds a variable from constant sequence of given shape with value 0.1
        initial = tf.constant(0.1, shape=shape)
        return tf.Variable(initial)
    else:
      # Builds a variable from a given tensor
      return tf.Variable(init)

def peform2DConvolution(x, W):
    """
    Applies a 2-D convolutional filter for the given input 'x' using weights 'W'.
    """
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

def performMaxPooling(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

convnet = pickle.load(open(convnet_file))

W_conv1 = buildWeightVariable([5, 5, 1, 32], init = convnet['Wc1'])
b_conv1 = buildBiasVariable([32], init = convnet['bc1'])

W_conv2 = buildWeightVariable([5, 5, 32, 64], init = convnet['Wc2'])
b_conv2 = buildBiasVariable([64], init = convnet['bc2'])

W_fc1 = buildWeightVariable([7 * 7 * 64, 1024], init = convnet['Wfc1'])
b_fc1 = buildBiasVariable([1024], init = convnet['bfc1'])

def buildConvnet(x_image):
    
    h_conv1 = tf.nn.relu(peform2DConvolution(x_image, W_conv1) + b_conv1)
    h_pool1 = performMaxPooling(h_conv1)
    
    h_conv2 = tf.nn.relu(peform2DConvolution(h_pool1, W_conv2) + b_conv2)
    h_pool2 = performMaxPooling(h_conv2)
    
    h_pool2_flat = tf.reshape(h_pool2, [-1, 7 * 7 * 64])
    h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)
    
    return h_fc1

def buildRecurrentNeuralNetwork(_X, _istate, _weights, _biases):
    
    # Reshape _X to prepare input to hidden activation by permuting first
    # and second dimensions.
    #
    # Input shape:  (batch_size, n_steps, img_width, img_height, n_color_channels)
    # Output shape: (n_steps, batch_size, img_width, img_height, n_color_channels)
    _X = tf.transpose(_X, [1, 0, 2, 3, 4])
    
    sequence = []
    
    for seqIdx in range(n_steps):
        if seqIdx > 0:
            sequence.append(buildConvnet(_X[0,:,:,:,:]))
        if seqIdx > 1:
            sequence.append(buildConvnet(_X[1,:,:,:,:]))
        if seqIdx > 2:
            sequence.append(buildConvnet(_X[2,:,:,:,:]))
        if seqIdx > 3:
            sequence.append(buildConvnet(_X[3,:,:,:,:]))
        if seqIdx > 4:
            sequence.append(buildConvnet(_X[4,:,:,:,:]))
        if seqIdx > 5:
            sequence.append(buildConvnet(_X[5,:,:,:,:]))
        if seqIdx > 6:
            sequence.append(buildConvnet(_X[6,:,:,:,:]))
        if seqIdx > 7:
            sequence.append(buildConvnet(_X[7,:,:,:,:]))
        if seqIdx > 8:
            sequence.append(buildConvnet(_X[8,:,:,:,:]))
        if seqIdx > 9:
            sequence.append(buildConvnet(_X[9,:,:,:,:]))
        if seqIdx > 10:
            sequence.append(buildConvnet(_X[10,:,:,:,:]))
    
    # Define a lstm cell with tensorflow
    lstm_cell = rnn_cell.BasicLSTMCell(n_hidden, forget_bias=1.0)
    
    # Get lstm cell output
    outputs, states = rnn.rnn(lstm_cell, sequence, initial_state=_istate)
    
    # Linear activation
    # Get inner loop last output
    out1 = tf.nn.relu(tf.matmul(outputs[-1], _weights['out1']) + _biases['out1'])
    out2 = tf.matmul(out1, _weights['out2']) + _biases['out2']
    
    return out2

# Graph input
x = tf.placeholder("float", [None, n_steps, 28, 28, 1])
y = tf.placeholder("float", [None, 1])

# Tensorflow LSTM cell requires 2 x n_hidden length (state & cell)
istate = tf.placeholder("float", [None, 2 * n_hidden])

# Define hidden layer weights
weights = {
    'hidden': tf.Variable(tf.random_normal([n_input, n_hidden])),
    'out1': tf.Variable(tf.truncated_normal([n_hidden,512])),
    'out2': tf.Variable(tf.truncated_normal([512, 1]))
}

biases = {
    'hidden': tf.Variable(tf.random_normal([n_hidden])),
    'out1': tf.Variable(tf.zeros([512])),
    'out2': tf.Variable(tf.zeros([1]))
}

pred = buildRecurrentNeuralNetwork(x, istate, weights, biases)

# Define loss using squared mean
cost = tf.reduce_mean(tf.nn.l2_loss(pred - y))

# Define optimizer as Adam Optimizer
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

# Evaluate model
correct_pred = tf.equal(tf.round(pred), tf.round(y))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

print "  Finished"

## In[3]: Train agent

training_iters = args.training_iters
display_step = args.display_step

print "- Training agent"

'''
trainer = AgentTrainer(agent, training_iters, display_step, n_first_digit_length, n_second_digit_length)
trainer.train(digits, digit_labels, symbols, symbol_labels)
'''

# Initialize variables
init = tf.initialize_all_variables()

# Launch the graph
with tf.Session() as session:
    session.run(init)
    step = 1
    # Keep training until reach max iterations
    while step < training_iters:
        # Generate random sequence from trainig data
        batch_xs, batch_ys, batch_ops = generate_sequence(digits, digit_labels, symbols, symbol_labels, batch_size, n_first_digit_length, n_second_digit_length)
        # Fit training using batch data
        session.run(optimizer, feed_dict={x: batch_xs, y: batch_ys, istate: np.zeros((batch_size, 2 * n_hidden))})
        if step % display_step == 0:
            # Calculate batch accuracy, loss and prediction
            loss, acc, prd = session.run([cost, accuracy, pred], feed_dict={x: batch_xs, y: batch_ys, istate: np.zeros((batch_size, 2 * n_hidden))})
            print "  Iteration=" + str(step) + " Minibatch_Error=" + "{:.6f}".format(np.sqrt(loss)) + " Training_Accuracy=" + "{:.5f}".format(acc)
            #print " ", batch_ops[0], batch_ys[0], prd[0]
        # Increase step
        step += 1

print "  Finished"

## In[4]: Test agent
'''
test_images_file = args.test_images_file
test_labels_file = args.test_labels_file

print "- Loading testing data"

digits, digit_labels, symbols, symbol_labels = load_data(test_images_file, test_labels_file)

print "  Finished"

print "- Testing agent"

batch_ys, batch_ops, pred = trainer.test(digits, digit_labels, symbols, symbol_labels)

print '  GT', batch_ys, batch_ops
print '  Pred', pred
'''

