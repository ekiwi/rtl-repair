source /etc/profile.d/modules.sh
module load vcs/2017.12-SP2-1

cur_dir=`pwd`

cd $3

echo $1 $2
sed "s/$1/$2/g" vcs_sim_command_padder > vcs_sim_command_buggy_padder

cat vcs_sim_command_buggy_padder
`cat vcs_sim_command_buggy_padder`

rm vcs_sim_command_buggy_padder

cp output_test_padder_t1.txt $cur_dir/output_test_padder_t1.txt
rm output_test_padder_t1.txt

cd $cur_dir

