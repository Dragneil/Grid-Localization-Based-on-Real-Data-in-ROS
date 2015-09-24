#!/usr/bin/env python
import rospy
import roslib
import rosbag
from std_msgs.msg import String
import numpy as n
import math
import tf
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Point
pt_count = 0
tagnum_x = [125, 125, 125, 425, 425, 425]
tagnum_y = [525, 325, 125, 125, 325, 525]


def degtorad(x):
    return (x*math.pi)/180.0

def angle(a,b,x,y):
    xdiff = a - x
    ydiff = b - y
    rad = math.atan2(ydiff,xdiff)
    #if rad < 0:
    #   rad = 2*math.pi - abs(rad)
    return rad
def rotate(slope, angle):
    if(angle - slope > 0 and angle - slope < math.pi):
        return -1*(math.pi - abs(abs(slope - angle) - math.pi))
    else:
        return (math.pi - abs(abs(slope - angle) - math.pi))
def funct(a,b,c,x,y,z):
    p1 = n.array(((a*20.0)+10.0,(b*20.0)+10.0))
    p2 = n.array(((x*20.0)+10.0,(y*20.0)+10.0))
    dist = n.linalg.norm(p1-p2)
    slope = angle((a*20.0)+10.0,(b*20.0)+10.0,(x*20.0)+10.0,(y*20.0)+10.0)
    #if slope < 0 :
    #    slope = 2*math.pi - abs(slope)
    r1 = rotate(degtorad(((c*40.0) + 20.0)),slope)

    #print "slope: {1}", format(angle((a*20)+10,(b*20)+10,(x*20)+10,(y*20)+10))
    #print "current:: {1}", format(degtorad(c*10 + 5))
    #print "r1: {1}", format(r1)
    r2 = rotate(slope,degtorad((z*40)+20))
    #print "final: {1}", format(degtorad((z*10)+5))
    #print "r2: {1}", format(r2)
    return r1,dist,r2


def gaussian(error,sigma):
    fact = 1/math.sqrt(2.0*math.pi*math.sqrt(sigma))
    prob = fact * math.exp(-1*(error**2)/(2.0*sigma))
    return prob


def init_grid(pub):
    file_loc = rospy.get_param('~bag_file')
    #bag = rosbag.Bag('/home/krishna/catkin_ws/src/lab3/src/grid.bag','r')
    bag = rosbag.Bag(file_loc,'r')
    sigma_rot = degtorad(20.0)
    sigma_trans = 10.0

    #bag = rosbag.Bag('grid.bag','r')
    #grid = [[[0 for col in range(18)]for row in range(35)] for x in range(35)]
    grid = n.zeros((35,35,9),dtype=n.float64)
    grid[11][27][5] = 1.0
    threshold = 0.05
    line_strip = Marker()
    line_strip.header.frame_id = "/base_link"
    line_strip.header.stamp = rospy.Time.now()
    line_strip.action = Marker.ADD
    line_strip.lifetime = rospy.Time(0)
    line_strip.scale.x = 0.1
    line_strip.scale.y = 0.1
    line_strip.scale.z = 0.1
    line_strip.color.a = 1.0
    line_strip.color.r = 0.0
    line_strip.color.g = 1.0
    line_strip.color.b = 0.0
    line_strip.ns = "pts_line"
    line_strip.id = 0
    line_strip.type = Marker.LINE_STRIP
    prev = Point()
    prev.x = 11 * 0.2 + 0.1
    prev.y = 27 * 0.2 + 0.1
    prev.z = 0
    line_strip.points.append(prev)
    print "PUBLISHER: " + str(pub)

    for topic, msg, t in bag.read_messages(topics = ['Movements','Observations']):
        if(topic == 'Movements'):
            newgrid = n.zeros((35,35,9),dtype=n.float64)
            sumprob = 0.0
            max = 0.0
            print "Running: "
            for a in range(35):
               for b in range(35):
                    for c in range(9):

                        for x in range(35):
                            for y in range(35):
                                for z in range(9):
                                    if(a == x and b == y and c == z):
                                        continue
                                    if(grid[x][y][z]>threshold):
                                        #print(x)
                                        r1,t1,r2 = funct(x,y,z,a,b,c)
                                        quaternion = (msg.rotation1.x,msg.rotation1.y,msg.rotation1.z,msg.rotation1.w)
                                        euler = tf.transformations.euler_from_quaternion(quaternion)
                                        act_r1 = euler[2]#convert to degrees we get it in rads
                                        #print(r1,act_r1)
                                        errorr1 = act_r1 - r1
                                        quaternion2 = (msg.rotation2.x,msg.rotation2.y,msg.rotation2.z,msg.rotation2.w)
                                        euler2 = tf.transformations.euler_from_quaternion(quaternion2)
                                        act_r2 = euler2[2]
                                        #print(r2,act_r2)
                                        errorr2 = act_r2 - r2
                                        act_t1 = msg.translation * 100
                                        errort1 = act_t1 - t1
                                        newgrid[a][b][c] += (gaussian(errorr1,sigma_rot) * gaussian(errort1,sigma_trans) * gaussian(errorr2,sigma_rot) * grid[x][y][z])
                                        #print "gaussian _ r1 {0}".format(str(gaussian(errorr1,10.0)))

                        if(max < newgrid[a][b][c]):
                            max = newgrid[a][b][c]
                            print "a {0}: b: {1} c :{2} grid prob {3}".format(a,b,c,newgrid[a][b][c])
                                    #if(grid[a][b][c]>0.01):


            #norm = n.sum(newgrid)
            #print "sum of grid: " + str(norm)
            grid = newgrid
            print(grid)
            max_prob = n.amax(grid)
            print "max prob motion: " + str(max_prob)
            indexes = n.unravel_index(n.argmax(grid),grid.shape)
            print(indexes)
            print"Observations started! "
        if(topic == 'Observations'):
            #oservation_probs = n.zeros((grid.shape),dtype=n.float64)
            for x in range(35):
                for y in range(35):
                    for z in range(9):
                        tag = msg.tagNum
                        #print "tagnum_y {0}: y: {1} tagnum x :{2} x {3} tag num {4}".format(str(tagnum_y[tag]),str(y),str(tagnum_x[tag]),str(x),str(tag))
                        calculated_range = math.sqrt(((tagnum_y[tag] - ((y * 20.0) + 10.0))**2)+((tagnum_x[tag] - ((x * 20.0) + 10.0))**2))
                        #print "cal range: " + str(calculated_range)
                        line_slope = angle(tagnum_x[tag],tagnum_y[tag],(x * 20.0) + 10.0, (y * 20.0) + 10.0)
                        if line_slope < 0:
                            line_slope = 2 * math.pi - abs(line_slope)
                    #tag points se x,y draw a line and calculate the bearing
                        calculated_bearing = rotate(line_slope,degtorad((z * 40.0) + 20.0))
                        #print "cal bearing: " + str(calculated_bearing)
                        error_range = calculated_range - (msg.range * 100)
                        #print "Msg range: " +str( msg.range)
                        #print  "error range: " + str(error_range)
                        quaternion3 = (msg.bearing.x,msg.bearing.y,msg.bearing.z,msg.bearing.w)
                        euler3 = tf.transformations.euler_from_quaternion(quaternion3)
                        act_bearing = euler3[2]#convert to degrees we get it in rads
                        error_bearing = calculated_bearing - act_bearing
                        #print "msg bearing: " + str(act_bearing)
                        #print  " error bearing: " + str(error_bearing)
                        range_prob = gaussian(error_range,10.0)
                        bearing_prob = gaussian(error_bearing,sigma_rot)
                        #fact_obs = 1/math.sqrt(2.0*math.pi*5.0)
                        #print "fact_obs: " + str(fact_obs)
                        #bearing_prob = fact_obs * math.exp(-(error_bearing**2/(2.0*sigma_rot*sigma_rot)))
                        #oservation_probs[x][y][z] = range_prob * bearing_prob

                        grid[x][y][z] *= (range_prob*bearing_prob)
                        #if x < 5 and y < 5:
                        #    print "error range: " + str(error_range)
                        #    print "cal range: " + str(calculated_range)
                        #    print "Msg range: " +str( msg.range)
                        #    print"grid prob: " + str(grid[x][y][z])
                        #    print (grid[x][y][z], range_prob, bearing_prob)
                        sumprob += grid[x][y][z]
                        #print "grid prob sum: " + str(sumprob)


            print "Norm: " + str(sumprob)
            grid = grid/sumprob
            print "Grid sum : " + str(n.sum(grid))
            print "max prob: " + str(n.amax(grid))
            indexofmaxprob = n.unravel_index(n.argmax(grid),grid.shape)
            print "max prob at: " + str(indexofmaxprob)

            drawlandmark(pub)

            pointss = Point()
            pointss.x = indexofmaxprob[0] * 0.2 + 0.1
            pointss.y = indexofmaxprob[1] * 0.2 + 0.1
            pointss.z = 0
            line_strip.points.append(pointss)
            pub.publish(line_strip)


def drawlandmark(pub):
    global pt_count
    points_tag = Marker()
    points_tag.header.frame_id = "/base_link"
    points_tag.action = Marker.ADD
    points_tag.header.stamp = rospy.Time.now()
    points_tag.lifetime = rospy.Time(0)
    points_tag.scale.x = 0.1;
    points_tag.scale.y = 0.1;
    points_tag.scale.z = 0.1;
    points_tag.color.a = 1.0;
    points_tag.color.r = 1.0;
    points_tag.color.g = 0.0;
    points_tag.color.b = 0.0;
    points_tag.ns = "pts_line"
    pt_count+=1
    points_tag.id = pt_count
    points_tag.type = Marker.POINTS
    for x in range(6):
        p1 = Point()
        p1.x = tagnum_x[x]/100
        p1.y = tagnum_y[x]/100
        p1.z = 0
        points_tag.points.append(p1)
    pub.publish(points_tag)

if __name__== '__main__':
    rospy.init_node("localizer")

    pub = rospy.Publisher('visualization_marker',Marker,queue_size=10)
    drawlandmark(pub)
    init_grid(pub)
    rospy.spin()
